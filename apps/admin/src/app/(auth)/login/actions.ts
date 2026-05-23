'use server';

import { isRedirectError } from 'next/dist/client/components/redirect';
import { z } from 'zod';

import { signIn } from '@/lib/auth/auth';

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  nextPath: z.string().startsWith('/').default('/dashboard'),
});

export interface CredentialsActionResult {
  readonly ok: boolean;
  readonly message?: string;
}

export async function signInWithCredentialsAction(
  raw: unknown,
): Promise<CredentialsActionResult> {
  const parsed = credentialsSchema.safeParse(raw);
  if (!parsed.success) {
    return { ok: false, message: 'Please enter a valid email and password.' };
  }
  try {
    await signIn('credentials', {
      email: parsed.data.email,
      password: parsed.data.password,
      redirectTo: parsed.data.nextPath,
    });
    return { ok: true };
  } catch (cause) {
    // NextAuth v5 issues a redirect on success; re-throw so Next.js processes it.
    if (isRedirectError(cause)) throw cause;
    return {
      ok: false,
      message: cause instanceof Error ? cause.message : 'Sign-in failed.',
    };
  }
}

export async function signInWithProviderAction(
  provider: 'google' | 'apple' | 'telegram',
  nextPath: string,
): Promise<{ ok: boolean; message?: string }> {
  // SILK-0155: Route through the real OAuth provider when credentials are
  // present in env. Return an error result (no redirect) when they are not
  // configured so the client can surface an informative toast.
  const providerConfigured =
    provider === 'google'
      ? Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET)
      : false; // Apple / Telegram not wired yet.

  if (!providerConfigured) {
    return {
      ok: false,
      message: `${provider.charAt(0).toUpperCase() + provider.slice(1)} OAuth is not configured yet. Use email/password login.`,
    };
  }

  try {
    await signIn(provider, { redirectTo: nextPath });
    return { ok: true };
  } catch (cause) {
    if (isRedirectError(cause)) throw cause;
    return {
      ok: false,
      message: cause instanceof Error ? cause.message : `${provider} sign-in failed.`,
    };
  }
}
