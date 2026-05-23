import NextAuth, { type DefaultSession } from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import Google from 'next-auth/providers/google';
import { z } from 'zod';

import { permissionsForTrustTier } from '@/lib/rbac/permissions';
import type { LoginResponse, MeResponse } from '@/types/api';

/**
 * NextAuth v5 (Auth.js) wiring against the SilkLens FastAPI backend.
 *
 *   - Credentials provider posts to `POST /v1/auth/login` and stashes the
 *     `access_token` + `refresh_token` + expiry on the JWT.
 *   - The JWT callback performs a silent refresh against `/v1/auth/refresh`
 *     when the access token is within `REFRESH_THRESHOLD_MS` of expiry.
 *   - `/v1/auth/me` is called on first sign-in to cache the user's tenant and
 *     residency so server fetches don't have to round-trip every render.
 */

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  tenantId: z.string().optional(),
});

const loginResponseSchema = z.object({
  user: z.object({
    id: z.string(),
    pub_id: z.string(),
    tenant_id: z.string(),
    residency_region: z.enum(['uz', 'eu', 'us', 'global']),
    trust_tier: z.string(),
    preferred_locale: z.string(),
    preferred_timezone: z.string(),
    is_verified: z.boolean(),
  }),
  tokens: z.object({
    access_token: z.string(),
    refresh_token: z.string(),
    token_type: z.literal('Bearer'),
    expires_in: z.number().int().positive(),
  }),
});

declare module 'next-auth' {
  interface Session {
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpiresAt?: number;
    error?: 'RefreshAccessTokenError';
    user: {
      id: string;
      pubId: string;
      tenantId: string;
      /** Tenant slug (e.g. "silklens") — used for branding and tenant-scoped API calls. */
      tenantSlug: string;
      residencyRegion: string;
      trustTier: string;
      preferredLocale: string;
      permissions: readonly string[];
    } & DefaultSession['user'];
  }

  interface User {
    pubId?: string;
    tenantId?: string;
    /** Tenant slug resolved from /v1/admin/tenants or env NEXT_PUBLIC_DEFAULT_TENANT_SLUG. */
    tenantSlug?: string;
    residencyRegion?: string;
    trustTier?: string;
    preferredLocale?: string;
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpiresAt?: number;
  }
}

// SilkLens custom JWT fields persisted across NextAuth JWT callbacks.
interface SilkJWT {
  accessToken?: string;
  refreshToken?: string;
  accessTokenExpiresAt?: number;
  pubId?: string;
  tenantId?: string;
  /** Tenant slug — persisted in JWT so every server render can use it without a DB round-trip. */
  tenantSlug?: string;
  residencyRegion?: string;
  trustTier?: string;
  preferredLocale?: string;
  permissions?: readonly string[];
  error?: 'RefreshAccessTokenError';
  sub?: string;
  [key: string]: unknown;
}

const REFRESH_THRESHOLD_MS = 60_000; // refresh 60s before expiry

function resolveApiBase(): string {
  return process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL;
}

// SILK-0156: permissionsForTrustTier is now the canonical export from
// src/lib/rbac/permissions.ts — imported above and used in jwt callback.

async function callLogin(
  email: string,
  password: string,
  tenantId: string | undefined,
): Promise<LoginResponse> {
  const url = `${resolveApiBase().replace(/\/+$/, '')}/v1/auth/login`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      email,
      password,
      ...(tenantId ? { tenant_id: tenantId } : {}),
    }),
    cache: 'no-store',
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: { message?: string } | string };
      if (typeof body.detail === 'string') detail = body.detail;
      else if (body.detail?.message) detail = body.detail.message;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const json = await res.json();
  return loginResponseSchema.parse(json) as LoginResponse;
}

async function callRefresh(refreshToken: string): Promise<LoginResponse | null> {
  const url = `${resolveApiBase().replace(/\/+$/, '')}/v1/auth/refresh`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: 'no-store',
  });
  if (!res.ok) return null;
  try {
    return loginResponseSchema.parse(await res.json()) as LoginResponse;
  } catch {
    return null;
  }
}

async function callMe(accessToken: string): Promise<MeResponse | null> {
  const url = `${resolveApiBase().replace(/\/+$/, '')}/v1/auth/me`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
  });
  if (!res.ok) return null;
  return (await res.json()) as MeResponse;
}

export const { auth, handlers, signIn, signOut } = NextAuth({
  trustHost: true,
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
  },
  providers: [
    Credentials({
      name: 'Email & password',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
        tenantId: { label: 'Tenant', type: 'text' },
      },
      async authorize(credentials) {
        const parsed = credentialsSchema.safeParse(credentials);
        if (!parsed.success) return null;
        try {
          const login = await callLogin(
            parsed.data.email,
            parsed.data.password,
            parsed.data.tenantId,
          );
          const expiresAt = Date.now() + login.tokens.expires_in * 1000;
          // /me confirms the token works and refreshes the user shape.
          const me = await callMe(login.tokens.access_token);
          const user = me?.user ?? login.user;
          // SILK-0168: tenantSlug is not yet returned by /me.
          // Fall back to NEXT_PUBLIC_DEFAULT_TENANT_SLUG so branding calls
          // use the correct tenant without a separate tenant API round-trip.
          const tenantSlug =
            process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'silklens';
          return {
            id: user.id,
            name: parsed.data.email,
            email: parsed.data.email,
            pubId: user.pub_id,
            tenantId: user.tenant_id,
            tenantSlug,
            residencyRegion: user.residency_region,
            trustTier: user.trust_tier,
            preferredLocale: user.preferred_locale,
            accessToken: login.tokens.access_token,
            refreshToken: login.tokens.refresh_token,
            accessTokenExpiresAt: expiresAt,
          };
        } catch (cause) {
          // NextAuth swallows non-CredentialsSignin throws; null = invalid.
          // We surface the underlying message via the URL so the form can
          // render it.
          if (process.env.NODE_ENV !== 'production') {
            // eslint-disable-next-line no-console
            console.error('[auth] login failed:', cause);
          }
          return null;
        }
      },
    }),
    // SILK-0155: Google OAuth — only registered when both env vars are present.
    // Callback URI to add in Google Cloud Console:
    //   http://localhost:3001/api/auth/callback/google  (dev)
    //   https://<prod-domain>/api/auth/callback/google  (prod)
    ...(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET
      ? [
          Google({
            clientId: process.env.AUTH_GOOGLE_ID,
            clientSecret: process.env.AUTH_GOOGLE_SECRET,
          }),
        ]
      : []),
  ],
  callbacks: {
    // SILK-0155: Exchange Google access_token for SilkLens JWT via the backend.
    // For Credentials the signIn callback is not invoked; authorize() handles it.
    async signIn({ account }) {
      if (account?.provider === 'google') {
        if (!account.access_token) return false;
        try {
          const base = resolveApiBase().replace(/\/+$/, '');
          const response = await fetch(`${base}/v1/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ access_token: account.access_token }),
            cache: 'no-store',
          });
          if (!response.ok) return false;
          const data = (await response.json()) as LoginResponse;
          // Stash SilkLens tokens on the account object so the jwt callback
          // can pick them up via the `account` parameter on initial sign-in.
          (account as Record<string, unknown>).silklensAccessToken =
            data.tokens.access_token;
          (account as Record<string, unknown>).silklensRefreshToken =
            data.tokens.refresh_token;
          (account as Record<string, unknown>).silklensExpiresIn =
            data.tokens.expires_in;
          (account as Record<string, unknown>).silklensUser = data.user;
          return true;
        } catch {
          return false;
        }
      }
      // All other providers (Credentials authorize() already returned the user).
      return true;
    },

    async jwt({ token, user, account, trigger }) {
      const t = token as SilkJWT;
      // Initial sign-in — Credentials provider populates `user` with tokens.
      if (user && account?.provider === 'credentials') {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.accessTokenExpiresAt = user.accessTokenExpiresAt;
        token.pubId = user.pubId;
        token.tenantId = user.tenantId;
        token.tenantSlug = user.tenantSlug ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'silklens';
        token.residencyRegion = user.residencyRegion;
        token.trustTier = user.trustTier ?? 'authenticated';
        token.preferredLocale = user.preferredLocale;
        token.permissions = permissionsForTrustTier(user.trustTier ?? 'authenticated');
        token.error = undefined;
        return token;
      }

      // SILK-0155: Google OAuth — tokens were stashed on account in signIn().
      if (account?.provider === 'google') {
        const acc = account as Record<string, unknown>;
        const silklensUser = acc.silklensUser as
          | { pub_id: string; tenant_id: string; residency_region: string; trust_tier: string; preferred_locale: string }
          | undefined;
        token.accessToken = acc.silklensAccessToken as string | undefined;
        token.refreshToken = acc.silklensRefreshToken as string | undefined;
        token.accessTokenExpiresAt =
          typeof acc.silklensExpiresIn === 'number'
            ? Date.now() + acc.silklensExpiresIn * 1000
            : undefined;
        token.pubId = silklensUser?.pub_id;
        token.tenantId = silklensUser?.tenant_id;
        token.tenantSlug = process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'silklens';
        token.residencyRegion = silklensUser?.residency_region;
        const tier = silklensUser?.trust_tier ?? 'authenticated';
        token.trustTier = tier;
        token.preferredLocale = silklensUser?.preferred_locale;
        token.permissions = permissionsForTrustTier(tier);
        token.error = undefined;
        return token;
      }

      // Force-refresh on explicit `update()` calls.
      if (trigger === 'update' && t.refreshToken) {
        const refreshed = await callRefresh(t.refreshToken);
        if (refreshed) {
          t.accessToken = refreshed.tokens.access_token;
          t.refreshToken = refreshed.tokens.refresh_token;
          t.accessTokenExpiresAt =
            Date.now() + refreshed.tokens.expires_in * 1000;
          t.error = undefined;
          return t;
        }
        t.error = 'RefreshAccessTokenError';
        return t;
      }

      // Silent refresh near expiry.
      const expiresAt = t.accessTokenExpiresAt;
      if (
        expiresAt !== undefined &&
        Date.now() >= expiresAt - REFRESH_THRESHOLD_MS &&
        t.refreshToken
      ) {
        const refreshed = await callRefresh(t.refreshToken);
        if (refreshed) {
          t.accessToken = refreshed.tokens.access_token;
          t.refreshToken = refreshed.tokens.refresh_token;
          t.accessTokenExpiresAt =
            Date.now() + refreshed.tokens.expires_in * 1000;
          t.error = undefined;
        } else {
          t.error = 'RefreshAccessTokenError';
        }
      }

      return t;
    },
    async session({ session, token }) {
      const t = token as SilkJWT;
      session.accessToken = t.accessToken;
      session.refreshToken = t.refreshToken;
      session.accessTokenExpiresAt = t.accessTokenExpiresAt;
      session.error = t.error;
      session.user.id = (t.sub as string | undefined) ?? session.user.id;
      session.user.pubId = t.pubId ?? '';
      session.user.tenantId =
        t.tenantId ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
      session.user.tenantSlug =
        t.tenantSlug ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'silklens';
      session.user.residencyRegion = t.residencyRegion ?? 'global';
      session.user.trustTier = t.trustTier ?? 'authenticated';
      session.user.preferredLocale = t.preferredLocale ?? 'uz';
      session.user.permissions = t.permissions ?? [];
      return session;
    },
  },
});
