// app/types/copertine.ts
export interface CopertineData {
    extracted_caption: string;
    kickerStr: string;
    date: string;
    isoDate: string; // Added for proper sorting
    extraction_timestamp?: string;
}

export interface CopertineEntry extends CopertineData {
    filename: string;
}

export interface PaginationInfo {
    total: number;
    offset: number;
    limit: number;
    hasMore: boolean;
}

export interface CopertineResponse {
    data: CopertineEntry[];
    pagination: PaginationInfo;
}