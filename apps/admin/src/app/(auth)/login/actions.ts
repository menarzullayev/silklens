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
): Promise<void> {
  // TODO(identity): once provider IDs/secrets are in `.env`, this will route
  // through the configured OAuth provider. Today it falls back to credentials
  // since no real provider is registered yet.
  await signIn('credentials', {
    email: `${provider}-demo@silklens.app`,
    password: 'demo',
    redirectTo: nextPath,
  });
}
