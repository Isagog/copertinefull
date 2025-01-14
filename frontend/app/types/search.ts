// app/types/search.ts

export interface SearchRequest {
  query: string;   // The search term
  mode: 'literal' | 'fuzzy';  // Search mode matching FastAPI
}

export interface SearchResult {
  testataName: string;
  editionId: string;
  editionDateIsoStr: string;
  editionImageFnStr: string;
  captionStr: string;
  kickerStr: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
}