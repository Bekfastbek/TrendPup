import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    // Primary path to the helix_detailed_data.json file
    const detailedFilePath = path.join(process.cwd(), '..', 'Twitter-scraper', 'helix_detailed_data.json');
    
    // Fallback path to the original helix_data.json file
    const fallbackFilePath = path.join(process.cwd(), '..', 'Twitter-scraper', 'helix_data.json');
    
    let data;
    let jsonData;
    
    // Try to read the detailed data file first
    if (fs.existsSync(detailedFilePath)) {
      try {
        data = fs.readFileSync(detailedFilePath, 'utf8');
        jsonData = JSON.parse(data);
        console.log('Successfully loaded detailed Helix data');
      } catch (detailedError) {
        console.error('Error reading helix_detailed_data.json:', detailedError);
        // If there's an error with the detailed data, try the fallback
        data = fs.readFileSync(fallbackFilePath, 'utf8');
        jsonData = JSON.parse(data);
        console.log('Using fallback Helix data');
      }
    } else {
      // If the detailed file doesn't exist, use the fallback
      data = fs.readFileSync(fallbackFilePath, 'utf8');
      jsonData = JSON.parse(data);
      console.log('Detailed data file not found, using fallback Helix data');
    }
    
    // Return the data
    return NextResponse.json(jsonData);
  } catch (error) {
    console.error('Error reading Helix data:', error);
    
    // If there's an error, return a 500 response
    return NextResponse.json(
      { error: 'Failed to fetch helix data' },
      { status: 500 }
    );
  }
} 