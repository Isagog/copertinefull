// app/api/copertine/route.ts
import { NextRequest } from 'next/server';
import pool from '@/app/lib/db';

const FTS_CONFIG = 'italian_unaccent';

const DEFAULT_LIMIT = 30;
const MAX_LIMIT = 100;

type Mode = 'esatta' | 'varianti';
type Scope = 'titolo' | 'tutto';
type Sort = 'data' | 'titolo' | 'rilevanza';

interface Criteria {
  q: string;
  mode: Mode;
  /** Whole word vs. substring. Only meaningful under `esatta`: `varianti`
   *  runs on a tsvector, which is tokenized and so always word-level. */
  whole: boolean;
  scope: Scope;
  sort: Sort;
  dir: 'ASC' | 'DESC';
  offset: number;
  limit: number;
}

/** parseInt('abc') is NaN, and Postgres rejects OFFSET 'NaN' with a 500. */
function clampInt(raw: string | null, fallback: number, min: number, max: number): number {
  const n = Number.parseInt(raw ?? '', 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(Math.max(n, min), max);
}

function parseCriteria(sp: URLSearchParams): Criteria {
  const q = sp.get('q')?.trim() ?? '';
  const mode: Mode = sp.get('mode') === 'varianti' ? 'varianti' : 'esatta';
  const scope: Scope = sp.get('scope') === 'titolo' ? 'titolo' : 'tutto';
  // Default to whole-word: it is the least surprising reading of "Esatta".
  const whole = sp.get('whole') !== '0';

  // Relevance only exists where there is a rank to sort on.
  const rawSort = sp.get('sort');
  const sort: Sort =
    rawSort === 'titolo'
      ? 'titolo'
      : rawSort === 'rilevanza' && mode === 'varianti' && q
        ? 'rilevanza'
        : rawSort === 'data'
          ? 'data'
          : mode === 'varianti' && q
            ? 'rilevanza'
            : 'data';

  return {
    q,
    mode,
    whole,
    scope,
    sort,
    dir: sp.get('dir') === 'asc' ? 'ASC' : 'DESC',
    offset: clampInt(sp.get('offset'), 0, 0, Number.MAX_SAFE_INTEGER),
    limit: clampInt(sp.get('limit'), DEFAULT_LIMIT, 1, MAX_LIMIT),
  };
}

/**
 * Escapes every character that is not a letter, digit or space. Blunt, but it
 * cannot under-escape: in a Postgres ARE, a backslash before a
 * non-alphanumeric character always means that literal character.
 */
function escapeRegex(s: string): string {
  return s.replace(/[^\p{L}\p{N}\s]/gu, '\\$&');
}

/**
 * `\y` asserts a word boundary, but only anchors correctly next to a word
 * character — asserting one beside leading/trailing punctuation would never
 * match (e.g. searching «guerra» with the quotes included).
 */
function wholeWordPattern(q: string): string {
  const left = /^[\p{L}\p{N}_]/u.test(q) ? '\\y' : '';
  const right = /[\p{L}\p{N}_]$/u.test(q) ? '\\y' : '';
  return `${left}${escapeRegex(q)}${right}`;
}

/** Builds the WHERE clause plus its single bind parameter ($1). */
function buildPredicate({ q, mode, whole, scope }: Criteria): { where: string; param: string } {
  if (mode === 'varianti') {
    const vector = scope === 'titolo' ? 'caption_vector' : 'search_vector';
    return {
      where: `${vector} @@ websearch_to_tsquery('${FTS_CONFIG}', $1)`,
      param: q,
    };
  }

  // Literal modes run through cop_norm() on both sides, which folds case,
  // accents and the two apostrophe forms the corpus mixes.
  const columns = scope === 'titolo' ? ['caption'] : ['caption', "coalesce(kicker, '')"];

  if (whole) {
    return {
      where: columns.map((c) => `cop_norm(${c}) ~ cop_norm($1)`).join(' OR '),
      param: wholeWordPattern(q),
    };
  }

  // strpos() rather than ILIKE '%'||$1||'%': a literal % or _ in the needle
  // would otherwise act as a wildcard and match everything.
  return {
    where: columns.map((c) => `strpos(cop_norm(${c}), cop_norm($1)) > 0`).join(' OR '),
    param: q,
  };
}

/**
 * Extra select-list columns. `varianti` gets a rank to sort on and
 * ts_headline markup; the literal modes are highlighted client-side, since
 * cop_norm() shifts offsets and so cannot drive server-side markup.
 */
function buildProjection({ mode, scope }: Criteria): string {
  if (mode !== 'varianti') return '';

  const vector = scope === 'titolo' ? 'caption_vector' : 'search_vector';
  const headline = (col: string) =>
    `ts_headline('${FTS_CONFIG}', ${col}, websearch_to_tsquery('${FTS_CONFIG}', $1),
       'HighlightAll=true, StartSel=<mark>, StopSel=</mark>') AS ${col}_hl`;

  return [
    `ts_rank(${vector}, websearch_to_tsquery('${FTS_CONFIG}', $1)) AS rank`,
    headline('caption'),
    // Out of scope under "Solo titolo" — highlighting it would mark text the
    // query never searched.
    ...(scope === 'tutto' ? [headline('kicker')] : []),
  ].join(',\n                 ');
}

/**
 * Whitelisted, never interpolated from raw input. `id` is appended as a
 * tiebreaker so OFFSET paging stays deterministic when the sort key ties.
 */
function buildOrderBy({ sort, dir }: Criteria): string {
  switch (sort) {
    case 'rilevanza':
      return `rank DESC, edition_date DESC, id DESC`;
    case 'titolo':
      return `cop_norm(caption) ${dir}, id DESC`;
    default:
      return `edition_date ${dir}, id DESC`;
  }
}

export async function GET(request: NextRequest) {
  const criteria = parseCriteria(request.nextUrl.searchParams);
  const { q, offset, limit } = criteria;

  try {
    const { where, param } = q
      ? buildPredicate(criteria)
      : { where: '', param: '' };

    const whereClause = q ? `WHERE ${where}` : '';
    const projection = q ? buildProjection(criteria) : '';
    const orderBy = buildOrderBy(criteria);

    // Bind params are positional, so the predicate's $1 must be omitted
    // entirely when browsing.
    const params = q ? [param, limit, offset] : [limit, offset];
    const [limitPos, offsetPos] = q ? ['$2', '$3'] : ['$1', '$2'];

    const dataQuery = `
      SELECT edition_id, edition_date, caption, kicker, image_filename${projection ? `,
             ${projection}` : ''}
      FROM editions
      ${whereClause}
      ORDER BY ${orderBy}
      LIMIT ${limitPos} OFFSET ${offsetPos}
    `;
    const countQuery = `
      SELECT count(*)::int AS total
      FROM editions
      ${whereClause}
    `;

    const [{ rows }, { rows: countRows }] = await Promise.all([
      pool.query(dataQuery, params),
      pool.query(countQuery, q ? [param] : []),
    ]);

    const total: number = countRows[0].total;

    return Response.json({
      data: rows.map(rowToEntry),
      pagination: { total, offset, limit, hasMore: offset + limit < total },
    });
  } catch (error) {
    console.error('Database query failed:', error);
    return Response.json({ error: 'Failed to fetch data' }, { status: 500 });
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function rowToEntry(row: any) {
  // edition_date comes back as a JS Date from pg for DATE columns
  const isoDate: string =
    row.edition_date instanceof Date
      ? row.edition_date.toISOString()
      : String(row.edition_date);

  return {
    extracted_caption: row.caption as string,
    kickerStr: (row.kicker ?? '') as string,
    date: new Date(isoDate).toLocaleDateString('it-IT'),
    filename: row.image_filename as string,
    isoDate,
    ...(row.caption_hl != null && { caption_hl: row.caption_hl as string }),
    ...(row.kicker_hl != null && { kicker_hl: row.kicker_hl as string }),
  };
}
