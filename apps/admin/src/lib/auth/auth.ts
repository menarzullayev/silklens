import NextAuth, { type DefaultSession } from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import { z } from 'zod';

/**
 * NextAuth v5 (Auth.js) wiring.
 *
 * This is intentionally minimal at the skeleton stage:
 *
 *   - Credentials provider with a zod-validated email/password shape that
 *     accepts any non-empty input and returns a fake admin user. This unblocks
 *     UI work without depending on the Identity service in services/api.
 *
 *   - JWT session strategy because the FastAPI backend is the source of truth
 *     for sessions; the admin only needs a forwardable access token.
 *
 * TODO(identity): Once the FastAPI auth endpoints are live, swap the
 * `authorize` callback for a fetch against `${API_INTERNAL_URL}/auth/login`
 * and add the real OAuth providers (Google, Apple, Telegram per
 * Project-Decisions §33).
 */

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

declare module 'next-auth' {
  interface Session {
    accessToken?: string;
    user: {
      id: string;
      tenantId: string;
      permissions: readonly string[];
    } & DefaultSession['user'];
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    tenantId?: string;
    permissions?: readonly string[];
  }
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
      },
      async authorize(credentials) {
        const parsed = credentialsSchema.safeParse(credentials);
        if (!parsed.success) return null;

        // TODO(identity): call FastAPI /auth/login here.
        // For now we return a deterministic stub so the dashboard renders.
        return {
          id: 'stub-admin-user',
          name: 'SilkLens Admin',
          email: parsed.data.email,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.tenantId = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
        // TODO(identity): fetch real permissions for this user via /auth/me.
        token.permissions = [
          'heritage:read',
          'heritage:write',
          'users:read',
          'moderation:read',
          'moderation:act',
          'ai-models:read',
          'monetization:read',
          'tenants:manage',
          'branding:manage',
          'analytics:read',
          'settings:manage',
        ];
        token.accessToken = 'stub-bearer-token';
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.user.id = token.sub ?? 'stub-admin-user';
      session.user.tenantId =
        token.tenantId ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
      session.user.permissions = token.permissions ?? [];
      return session;
    },
  },
});
