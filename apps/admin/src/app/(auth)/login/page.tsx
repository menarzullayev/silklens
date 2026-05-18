import { getTranslations } from 'next-intl/server';
import { ScanFace } from 'lucide-react';
import type { Metadata } from 'next';

import { LoginForm } from './login-form';

export const metadata: Metadata = {
  title: 'Sign in',
};

interface LoginPageProps {
  readonly searchParams?: { readonly next?: string; readonly error?: string };
}

export default async function LoginPage({
  searchParams,
}: LoginPageProps): Promise<JSX.Element> {
  const t = await getTranslations('auth');
  const tCommon = await getTranslations('common');
  const nextPath = searchParams?.next ?? '/dashboard';

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 p-6">
      <div className="w-full max-w-md space-y-6 rounded-xl border bg-card p-8 shadow-sm">
        <header className="space-y-2 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <ScanFace className="h-6 w-6" aria-hidden />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('loginTitle')}</h1>
          <p className="text-sm text-muted-foreground">{t('loginSubtitle')}</p>
        </header>
        <LoginForm
          nextPath={nextPath}
          error={searchParams?.error}
          labels={{
            email: t('email'),
            password: t('password'),
            signIn: t('signIn'),
            signInWithGoogle: t('signInWithGoogle'),
            signInWithApple: t('signInWithApple'),
            signInWithTelegram: t('signInWithTelegram'),
            cancel: tCommon('cancel'),
          }}
        />
      </div>
    </main>
  );
}
