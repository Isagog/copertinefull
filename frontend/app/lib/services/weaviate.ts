// app/lib/services/weaviate.ts
import weaviate, { WeaviateClient } from 'weaviate-ts-client';
import { API } from '../config/constants';

export function getWeaviateClient(): WeaviateClient {
    const config = {
        scheme: API.WEAVIATE_SCHEME,
        host: API.WEAVIATE_HOST,
    };

    return weaviate.client(config);
}