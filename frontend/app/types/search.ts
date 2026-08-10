// app/types/search.ts — the three search switches, shared by the form,
// the results page and the card renderer.

/** Corrispondenza: literal match vs. Italian stemmer. */
export type SearchMode = 'esatta' | 'varianti';

/** Ambito: title only, or title + kicker. */
export type SearchScope = 'titolo' | 'tutto';

export type SortField = 'data' | 'titolo' | 'rilevanza';
export type SortDirection = 'asc' | 'desc';

/** What the search form submits. */
export interface SearchOptions {
  mode: SearchMode;
  /**
   * Granularita: whole word vs. substring. Only meaningful under `esatta` —
   * `varianti` matches against a tsvector, which is tokenized and therefore
   * always word-level.
   */
  whole: boolean;
  scope: SearchScope;
}

/** A full request: what to search for, how to order it, and which page. */
export interface SearchCriteria extends SearchOptions {
  q: string;
  sort: SortField;
  dir: SortDirection;
  offset: number;
}

export const DEFAULT_OPTIONS: SearchOptions = {
  mode: 'esatta',
  whole: true,
  scope: 'tutto',
};

export const DEFAULT_CRITERIA: SearchCriteria = {
  ...DEFAULT_OPTIONS,
  q: '',
  sort: 'data',
  dir: 'desc',
  offset: 0,
};

/** Relevance only exists where the backend produces a rank to sort on. */
export function supportsRelevance(criteria: Pick<SearchCriteria, 'q' | 'mode'>): boolean {
  return criteria.q !== '' && criteria.mode === 'varianti';
}

export function criteriaToQueryString(criteria: SearchCriteria, limit: number): string {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(criteria.offset),
    sort: criteria.sort,
    dir: criteria.dir,
  });

  if (criteria.q) {
    params.set('q', criteria.q);
    params.set('mode', criteria.mode);
    params.set('scope', criteria.scope);
    params.set('whole', criteria.whole ? '1' : '0');
  }

  return params.toString();
}
