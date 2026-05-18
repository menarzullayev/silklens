'use client';

import { useState } from 'react';

import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { LOCALES, LOCALE_LABELS, type Locale } from '@/lib/i18n/config';

interface LocaleTextInputProps {
  readonly value: Record<string, string>;
  readonly onChange: (next: Record<string, string>) => void;
  readonly multiline?: boolean;
  readonly placeholder?: string;
  readonly className?: string;
  readonly inputId?: string;
}

/**
 * Tabbed multi-language text input. Each locale gets its own field; the
 * resulting record is shaped like the `i18n.text` jsonb columns the backend
 * stores (`{ en: "…", uz: "…" }`).
 */
export function LocaleTextInput({
  value,
  onChange,
  multiline = false,
  placeholder,
  className,
  inputId,
}: LocaleTextInputProps): JSX.Element {
  const [active, setActive] = useState<Locale>(LOCALES[0]);

  function update(locale: Locale, next: string): void {
    onChange({ ...value, [locale]: next });
  }

  return (
    <Tabs
      value={active}
      onValueChange={(v) => setActive(v as Locale)}
      className={cn('w-full', className)}
    >
      <TabsList>
        {LOCALES.map((locale) => (
          <TabsTrigger key={locale} value={locale}>
            {LOCALE_LABELS[locale]}
          </TabsTrigger>
        ))}
      </TabsList>
      {LOCALES.map((locale) => (
        <TabsContent key={locale} value={locale} className="mt-2">
          {multiline ? (
            <Textarea
              id={inputId ? `${inputId}-${locale}` : undefined}
              value={value[locale] ?? ''}
              onChange={(e) => update(locale, e.target.value)}
              placeholder={placeholder}
              rows={4}
            />
          ) : (
            <Input
              id={inputId ? `${inputId}-${locale}` : undefined}
              value={value[locale] ?? ''}
              onChange={(e) => update(locale, e.target.value)}
              placeholder={placeholder}
            />
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}
