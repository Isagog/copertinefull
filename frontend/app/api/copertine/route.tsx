// app/api/copertine/route.ts
import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';
import { CopertineData, CopertineEntry } from '@/app/types/copertine';

export async function GET() {
  try {
    // Get the file path from environment variable or fall back to default
    const jsonFilePath = process.env.COPERTINE_JSON_FILE || 'data/copertine.json';
    const filePath = path.join(process.cwd(), jsonFilePath);
    
    const fileContents = await fs.readFile(filePath, 'utf8');
    const data = JSON.parse(fileContents) as Record<string, CopertineData>;
    
    // Convert object to array format
    const copertineArray: CopertineEntry[] = Object.entries(data).map(([filename, value]) => ({
      filename,
      ...value
    }));

    return NextResponse.json(copertineArray);
  } catch (error) {
    console.error('Error reading copertine data:', error);
    return NextResponse.json(
      { error: 'Failed to load copertine data' },
      { status: 500 }
    );
  }
}