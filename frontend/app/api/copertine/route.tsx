// app/api/copertine/route.tsx
import { NextRequest, NextResponse } from 'next/server';
import { copertineCache } from '@app/lib/cache';
import { COPERTINEPERPAGE } from '@app/constants';

export async function GET(request: NextRequest) {
    try {
        const searchParams = request.nextUrl.searchParams;
        const offset = parseInt(searchParams.get('offset') || '0');
        const limit = parseInt(searchParams.get('limit') || String(COPERTINEPERPAGE));

        // Get data from cache (which will fetch from Weaviate if needed)
        const result = await copertineCache.get(offset);
        
        if (!result) {
            return NextResponse.json({ error: 'Failed to fetch data' }, { status: 500 });
        }

        return NextResponse.json({
            data: result.data,
            pagination: result.pagination,
            cached: true // For debugging
        });
    } catch (error) {
        console.error('Error in API route:', error);
        return NextResponse.json(
            { error: 'Failed to fetch data' },
            { status: 500 }
        );
    }
}