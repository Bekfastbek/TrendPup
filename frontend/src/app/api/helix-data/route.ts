import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    // Path to the helix_data.json file
    const filePath = path.join(process.cwd(), '..', 'Twitter-scraper', 'helix_data.json');
    
    // Read the file
    const data = fs.readFileSync(filePath, 'utf8');
    
    // Parse the JSON data
    const jsonData = JSON.parse(data);
    
    // Return the data
    return NextResponse.json(jsonData);
  } catch (error) {
    console.error('Error reading helix_data.json:', error);
    
    // If there's an error, return a 500 response
    return NextResponse.json(
      { error: 'Failed to fetch helix data' },
      { status: 500 }
    );
  }
} 