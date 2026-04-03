// app/api/copertine/route.ts
import { NextRequest } from 'next/server';
import pool from '@/app/lib/db';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const q = searchParams.get('q')?.trim() || '';
  const mode = searchParams.get('mode') === 'varianti' ? 'varianti' : 'esatta';
  const offset = parseInt(searchParams.get('offset') || '0');
  const limit = parseInt(searchParams.get('limit') || '30');

  try {
    if (q) {
      if (mode === 'esatta') {
        // Exact substring match — ILIKE, ordered by date
        const searchQuery = `
          SELECT edition_id, edition_date, caption, kicker, image_filename
          FROM editions
          WHERE caption ILIKE '%' || $1 || '%' OR kicker ILIKE '%' || $1 || '%'
          ORDER BY edition_date DESC LIMIT $2 OFFSET $3
        `;
        const countQuery = `
          SELECT count(*)::int AS total
          FROM editions
          WHERE caption ILIKE '%' || $1 || '%' OR kicker ILIKE '%' || $1 || '%'
        `;

        const [{ rows }, { rows: countRows }] = await Promise.all([
          pool.query(searchQuery, [q, limit, offset]),
          pool.query(countQuery, [q]),
        ]);

        const total: number = countRows[0].total;

        return Response.json({
          data: rows.map(rowToEntry),
          pagination: { total, offset, limit, hasMore: offset + limit < total },
        });
      } else {
        // Full-text search mode — stemmed, ranked by relevance
        const searchQuery = `
          SELECT edition_id, edition_date, caption, kicker, image_filename,
                 ts_rank(search_vector, websearch_to_tsquery('italian_unaccent', $1)) AS rank,
                 ts_headline('italian_unaccent', caption, websearch_to_tsquery('italian_unaccent', $1),
                   'HighlightAll=true, StartSel=<mark>, StopSel=</mark>') AS caption_hl,
                 ts_headline('italian_unaccent', kicker, websearch_to_tsquery('italian_unaccent', $1),
                   'HighlightAll=true, StartSel=<mark>, StopSel=</mark>') AS kicker_hl
          FROM editions
          WHERE search_vector @@ websearch_to_tsquery('italian_unaccent', $1)
          ORDER BY rank DESC LIMIT $2 OFFSET $3
        `;
        const countQuery = `
          SELECT count(*)::int AS total
          FROM editions
          WHERE search_vector @@ websearch_to_tsquery('italian_unaccent', $1)
        `;

        const [{ rows }, { rows: countRows }] = await Promise.all([
          pool.query(searchQuery, [q, limit, offset]),
          pool.query(countQuery, [q]),
        ]);

        const total: number = countRows[0].total;

        return Response.json({
          data: rows.map(rowToEntry),
          pagination: { total, offset, limit, hasMore: offset + limit < total },
        });
      }
    } else {
      // Browse mode — ordered by date desc
      const browseQuery = `
        SELECT edition_id, edition_date, caption, kicker, image_filename
        FROM editions ORDER BY edition_date DESC LIMIT $1 OFFSET $2
      `;
      const countQuery = `SELECT count(*)::int AS total FROM editions`;

      const [{ rows }, { rows: countRows }] = await Promise.all([
        pool.query(browseQuery, [limit, offset]),
        pool.query(countQuery),
      ]);

      const total: number = countRows[0].total;

      return Response.json({
        data: rows.map(rowToEntry),
        pagination: { total, offset, limit, hasMore: offset + limit < total },
      });
    }
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
