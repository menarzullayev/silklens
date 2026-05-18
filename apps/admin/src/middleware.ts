import { NextResponse, type NextRequest } from 'next/server';

import { TENANT_COOKIE, TENANT_HEADER, isValidUuid } from '@/lib/tenant/tenant';
import { LOCALE_COOKIE, isLocale } from '@/lib/i18n/config';

const PUBLIC_PATHS = ['/login', '/api/auth', '/_next', '/favicon', '/public'];

/**
 * Edge middleware:
 *   1. Resolve the active locale (cookie → Accept-Language → default) and
 *      forward it via a request header.
 *   2. Resolve the active tenant id (cookie → env default) and forward it as
 *      `X-Tenant-Id` so server components / API calls see it.
 *   3. Gate dashboard routes on the NextAuth `authjs.session-token` cookie.
 *      Full JWT verification happens in route handlers — middleware only
 *      checks presence to keep edge cold-start fast.
 */
export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  const requestHeaders = new Headers(request.headers);

  // --- Locale ---------------------------------------------------------------
  const cookieLocale = request.cookies.get(LOCALE_COOKIE)?.value;
  const locale = cookieLocale && isLocale(cookieLocale) ? cookieLocale : 'uz';
  requestHeaders.set('x-locale', locale);

  // --- Tenant ---------------------------------------------------------------
  const cookieTenant = request.cookies.get(TENANT_COOKIE)?.value;
  const tenantId =
    cookieTenant && isValidUuid(cookieTenant)
      ? cookieTenant
      : (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? '');
  if (tenantId) requestHeaders.set(TENANT_HEADER, tenantId);

  // --- Auth gate ------------------------------------------------------------
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  if (!isPublic) {
    const hasSession =
      request.cookies.has('authjs.session-token') ||
      request.cookies.has('__Secure-authjs.session-token');
    if (!hasSession) {
      const url = request.nextUrl.clone();
      url.pathname = '/login';
      url.searchParams.set('next', pathname);
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.svg|public).*)'],
};
