import NextAuth, { type DefaultSession } from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import { z } from 'zod';

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
      residencyRegion: string;
      trustTier: string;
      preferredLocale: string;
      permissions: readonly string[];
    } & DefaultSession['user'];
  }

  interface User {
    pubId?: string;
    tenantId?: string;
    residencyRegion?: string;
    trustTier?: string;
    preferredLocale?: string;
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpiresAt?: number;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpiresAt?: number;
    pubId?: string;
    tenantId?: string;
    residencyRegion?: string;
    trustTier?: string;
    preferredLocale?: string;
    permissions?: readonly string[];
    error?: 'RefreshAccessTokenError';
  }
}

const REFRESH_THRESHOLD_MS = 60_000; // refresh 60s before expiry

function resolveApiBase(): string {
  return process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL;
}

/**
 * Fetch the user's permission set. The backend doesn't currently expose a
 * dedicated endpoint, so we mirror the permissions we know are seeded for
 * the trust-tier the JWT was issued for. This list is kept in sync with
 * `permissions.slug` rows seeded by migration 0006.
 *
 * TODO(identity): expose `GET /v1/auth/me/permissions` and read it here.
 */
function permissionsForTrustTier(tier: string): readonly string[] {
  if (tier === 'super_admin' || tier === 'system_actor' || tier === 'staff') {
    return [
      'heritage:read',
      'heritage:create',
      'heritage:update',
      'heritage:delete',
      'heritage:moderate',
      'heritage:write',
      'users:read',
      'users:write',
      'users:ban',
      'moderation:read',
      'moderation:act',
      'ai-models:read',
      'ai-models:write',
      'ai:configure',
      'monetization:read',
      'monetization:write',
      'tenants:manage',
      'tenant:read',
      'tenant:create',
      'tenant:branding',
      'branding:manage',
      'analytics:read',
      'settings:manage',
      'system:settings',
      'system:feature_flags',
    ];
  }
  // Authenticated non-staff: read-only catalog access. Adjust as new tiers
  // are introduced.
  return ['heritage:read', 'analytics:read'];
}

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
          return {
            id: user.id,
            name: parsed.data.email,
            email: parsed.data.email,
            pubId: user.pub_id,
            tenantId: user.tenant_id,
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
  ],
  callbacks: {
    async jwt({ token, user, trigger }) {
      // Initial sign-in.
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.accessTokenExpiresAt = user.accessTokenExpiresAt;
        token.pubId = user.pubId;
        token.tenantId = user.tenantId;
        token.residencyRegion = user.residencyRegion;
        token.trustTier = user.trustTier ?? 'authenticated';
        token.preferredLocale = user.preferredLocale;
        token.permissions = permissionsForTrustTier(user.trustTier ?? 'authenticated');
        token.error = undefined;
        return token;
      }

      // Force-refresh on explicit `update()` calls.
      if (trigger === 'update' && token.refreshToken) {
        const refreshed = await callRefresh(token.refreshToken);
        if (refreshed) {
          token.accessToken = refreshed.tokens.access_token;
          token.refreshToken = refreshed.tokens.refresh_token;
          token.accessTokenExpiresAt =
            Date.now() + refreshed.tokens.expires_in * 1000;
          token.error = undefined;
          return token;
        }
        token.error = 'RefreshAccessTokenError';
        return token;
      }

      // Silent refresh near expiry.
      const expiresAt = token.accessTokenExpiresAt;
      if (
        expiresAt !== undefined &&
        Date.now() >= expiresAt - REFRESH_THRESHOLD_MS &&
        token.refreshToken
      ) {
        const refreshed = await callRefresh(token.refreshToken);
        if (refreshed) {
          token.accessToken = refreshed.tokens.access_token;
          token.refreshToken = refreshed.tokens.refresh_token;
          token.accessTokenExpiresAt =
            Date.now() + refreshed.tokens.expires_in * 1000;
          token.error = undefined;
        } else {
          token.error = 'RefreshAccessTokenError';
        }
      }

      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.refreshToken = token.refreshToken;
      session.accessTokenExpiresAt = token.accessTokenExpiresAt;
      session.error = token.error;
      session.user.id = (token.sub as string | undefined) ?? session.user.id;
      session.user.pubId = token.pubId ?? '';
      session.user.tenantId =
        token.tenantId ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
      session.user.residencyRegion = token.residencyRegion ?? 'global';
      session.user.trustTier = token.trustTier ?? 'authenticated';
      session.user.preferredLocale = token.preferredLocale ?? 'uz';
      session.user.permissions = token.permissions ?? [];
      return session;
    },
  },
});
