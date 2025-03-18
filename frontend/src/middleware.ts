import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Get response
  const response = NextResponse.next();

  // Add CORS headers
  response.headers.set('Access-Control-Allow-Origin', '*');
  response.headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, PATCH, DELETE');
  response.headers.set('Access-Control-Allow-Headers', 'X-Requested-With,content-type');
  response.headers.set('Access-Control-Allow-Credentials', 'true');

  return response;
}

// Configure which paths the middleware runs on
export const config = {
  matcher: [
    // Apply to all paths
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}; 