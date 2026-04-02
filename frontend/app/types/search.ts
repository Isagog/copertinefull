// app/types/search.ts — simplified for PostgreSQL FTS

export interface SearchRequest {
  query: string;
}

export interface SearchResponse {
  data: SearchEntry[];
  pagination: {
    total: number;
    offset: number;
    limit: number;
    hasMore: boolean;
  };
}

export interface SearchEntry {
  extracted_caption: string;
  kickerStr: string;
  date: string;
  filename: string;
  isoDate: string;
}
