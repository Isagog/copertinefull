import weaviate, { WeaviateClient } from 'weaviate-ts-client';
import { API } from '../config/constants';

export function getWeaviateClient(): WeaviateClient {
    return weaviate.client({
        scheme: API.WEAVIATE_SCHEME,
        host: API.WEAVIATE_HOST,
    });
}
