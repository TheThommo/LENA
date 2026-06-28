import { NextRequest, NextResponse } from 'next/server';

const BACKEND_ORIGIN =
  process.env.BACKEND_URL?.replace(/\/$/, '')
  || process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, '')
  || 'https://lena-production-health.up.railway.app';

/**
 * Proxy /api/* to the FastAPI backend in production.
 * next.config rewrites are unreliable in standalone Docker deploys; middleware
 * ensures same-origin /api calls still reach the backend as a fallback.
 */
export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const target = `${BACKEND_ORIGIN}${pathname}${search}`;

  const headers = new Headers(request.headers);
  headers.delete('host');

  return NextResponse.rewrite(new URL(target), {
    request: { headers },
  });
}

export const config = {
  matcher: '/api/:path*',
};
