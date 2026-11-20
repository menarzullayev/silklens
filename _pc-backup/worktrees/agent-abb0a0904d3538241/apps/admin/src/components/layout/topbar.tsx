import { LogOut } from 'lucide-react';

import { auth, signOut } from '@/lib/auth/auth';
import { getActiveTenantId, listKnownTenants } from '@/lib/tenant';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Breadcrumbs } from '@/components/layout/breadcrumbs';
import { LocaleSwitcher } from '@/components/layout/locale-switcher';
import { TenantSwitcher } from '@/components/layout/tenant-switcher';
import { ThemeToggle } from '@/components/layout/theme-toggle';
import { type Locale, DEFAULT_LOCALE, isLocale, LOCALE_COOKIE } from '@/lib/i18n/config';
import { cookies } from 'next/headers';

function resolveLocale(): Locale {
  const value = cookies().get(LOCALE_COOKIE)?.value;
  return value && isLocale(value) ? value : DEFAULT_LOCALE;
}

export async function Topbar(): Promise<JSX.Element> {
  const session = await auth();
  const tenants = listKnownTenants();
  const activeTenant = getActiveTenantId();
  const locale = resolveLocale();
  const initials = (session?.user?.name ?? session?.user?.email ?? 'AD')
    .split(/\s+/)
    .map((s) => s.charAt(0).toUpperCase())
    .slice(0, 2)
    .join('');

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background/95 px-6 backdrop-blur">
      <Breadcrumbs className="hidden flex-1 md:flex" />
      <div className="ml-auto flex items-center gap-2">
        <TenantSwitcher tenants={tenants} activeTenantId={activeTenant} />
        <Separator orientation="vertical" className="h-6" />
        <LocaleSwitcher activeLocale={locale} />
        <ThemeToggle />
        <Separator orientation="vertical" className="h-6" />
        <Avatar className="h-9 w-9">
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <form
          action={async () => {
            'use server';
            await signOut({ redirectTo: '/login' });
          }}
        >
          <Button variant="ghost" size="icon" type="submit" aria-label="Sign out">
            <LogOut className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </header>
  );
}
