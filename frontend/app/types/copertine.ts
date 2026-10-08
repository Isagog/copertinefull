// app/types/copertine.ts
export interface CopertineData {
    extracted_caption: string;
    kickerStr: string;
    date: string;
    isoDate: string; // Added for proper sorting
    extraction_timestamp?: string;
    caption_hl?: string;  // ts_headline output for search results
    kicker_hl?: string;   // ts_headline output for search results
}

export interface CopertineEntry extends CopertineData {
    filename: string;
    version?: number; // epoch seconds of the row's last write; busts image caches
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