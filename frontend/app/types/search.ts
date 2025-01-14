// app/types/search.ts
export type SearchStyle = 'literal' | 'fuzzy';

export interface SearchRequest {
  query: string;
  style: SearchStyle;
}

export interface SearchResponse {
  results: Array<{
    filename: string;
    extracted_caption: string;
    kickerStr: string;
    isoDate: string;
    score?: number;
  }>;
  total: number;
}