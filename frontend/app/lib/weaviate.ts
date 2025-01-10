// app/lib/weaviate.ts
import weaviate, { WeaviateClient } from 'weaviate-ts-client';

export function getWeaviateClient(): WeaviateClient {
    const config = {
        scheme: process.env.WEAVIATE_SCHEME || 'http',
        host: process.env.WEAVIATE_HOST || 'localhost:8080',
        // If you need to specify gRPC port or other options:
        // headers: { 'X-OpenAI-Api-Key': process.env.OPENAI_API_KEY }, // if needed
        // grpc: {
        //     port: 50500,
        //     secure: false,
        // },
    };

    return weaviate.client(config);
}

