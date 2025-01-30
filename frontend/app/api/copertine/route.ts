/**
 * Path: frontend/app/api/copertine/route.ts
 * Description: API route handler for copertine data
 * Proxies requests to the FastAPI backend
 */

import { NextRequest } from 'next/server';
import { API } from '@app/lib/config/constants';

export async function GET(request: NextRequest) {
    console.log('[/api/copertine] Handling request');
    const searchParams = request.nextUrl.searchParams;
    const offset = searchParams.get('offset') || '0';
    const limit = searchParams.get('limit') || '30';

    console.log('[/api/copertine] Request params:', { offset, limit });
    const authHeader = request.headers.get('Authorization');
    console.log('[/api/copertine] Auth header present:', !!authHeader);

    try {
        const url = `${API.BACKEND_URL}/copertine?offset=${offset}&limit=${limit}`;
        console.log('[/api/copertine] Forwarding to backend:', url);
        
        const response = await fetch(url, {
            headers: {
                'Authorization': request.headers.get('Authorization') || '',
                'Accept': 'application/json',
            },
            credentials: 'include',
        });

        console.log('[/api/copertine] Backend response status:', response.status);
        const responseText = await response.text();
        console.log('[/api/copertine] Backend response:', responseText);

        if (!response.ok) {
            console.error('[/api/copertine] Error response from backend');
            try {
                const error = JSON.parse(responseText);
                return Response.json(error, { status: response.status });
            } catch (parseError) {
                return Response.json({ error: responseText }, { status: response.status });
            }
        }

        try {
            const data = JSON.parse(responseText);
            console.log('[/api/copertine] Successfully parsed response');
            return Response.json(data);
        } catch (parseError) {
            console.error('[/api/copertine] Failed to parse response:', parseError);
            return Response.json(
                { error: 'Invalid response from backend' },
                { status: 500 }
            );
        }
    } catch (error) {
        console.error('[/api/copertine] Request error:', error);
        return Response.json(
            { error: 'Failed to fetch data', details: error instanceof Error ? error.message : 'Unknown error' },
            { status: 500 }
        );
    }
}
