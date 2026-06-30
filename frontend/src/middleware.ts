import { NextRequest, NextResponse } from 'next/server';

const BACKEND_ORIGIN =
  process.env.BACKEND_URL?.replace(/\/$/, '')
  || process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, '')
  || 'https://lena-production-health.up.railway.app';

function withSecurityHeaders(response: NextResponse): NextResponse {
  response.headers.set(
    'Strict-Transport-Security',
    'max-age=63072000; includeSubDomains; preload',
  );
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Content-Security-Policy', 'upgrade-insecure-requests');
  return response;
}

/**
 * - Force HTTPS on custom domains (Railway sets x-forwarded-proto)
 * - Proxy /api/* to FastAPI backend
 * - Security headers on all responses
 */
export function middleware(request: NextRequest) {
  const proto = request.headers.get('x-forwarded-proto');
  if (proto === 'http') {
    const httpsUrl = request.nextUrl.clone();
    httpsUrl.protocol = 'https:';
    return NextResponse.redirect(httpsUrl, 308);
  }

  const { pathname, search } = request.nextUrl;

  if (pathname.startsWith('/api')) {
    const target = `${BACKEND_ORIGIN}${pathname}${search}`;
    const headers = new Headers(request.headers);
    headers.delete('host');

    return withSecurityHeaders(
      NextResponse.rewrite(new URL(target), { request: { headers } }),
    );
  }

  return withSecurityHeaders(NextResponse.next());
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
  ],
};
