'use client';

import { Globe } from 'lucide-react';
import { useTransition } from 'react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { LOCALES, LOCALE_LABELS, type Locale } from '@/lib/i18n/config';
import { setActiveLocale } from '@/app/(dashboard)/_actions';

interface LocaleSwitcherProps {
  readonly activeLocale: Locale;
}

export function LocaleSwitcher({ activeLocale }: LocaleSwitcherProps): JSX.Element {
  const [pending, startTransition] = useTransition();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" disabled={pending} aria-label="Language">
          <Globe className="h-4 w-4" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {LOCALES.map((locale) => (
          <DropdownMenuItem
            key={locale}
            onSelect={() => {
              startTransition(async () => {
                await setActiveLocale(locale);
              });
            }}
          >
            <span className="flex-1">{LOCALE_LABELS[locale]}</span>
            {locale === activeLocale ? (
              <span className="text-xs text-muted-foreground">·</span>
            ) : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
