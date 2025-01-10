// app/types/weaviate.ts
export interface WeaviateItem {
    captionStr: string;
    editionDateIsoStr: string;
    editionId: string;
    editionImageFnStr: string;
    kickerStr: string;
    testataName: string;
}

export interface WeaviateGetResponse {
    data: {
        Get: {
            Copertine: WeaviateItem[];
        };
    };
}
