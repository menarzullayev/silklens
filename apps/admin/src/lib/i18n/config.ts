/**
 * i18n configuration — next-intl.
 *
 * Locales mirror Project-Decisions §8 (initial four launch locales). New
 * locales are added by dropping `<code>.json` into `src/messages/` and
 * appending the code here.
 */

export const LOCALES = ['uz', 'en', 'ru', 'zh'] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = 'uz';

export const LOCALE_COOKIE = 'silklens.locale';

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

export const LOCALE_LABELS: Readonly<Record<Locale, string>> = {
  uz: "O'zbek",
  en: 'English',
  ru: 'Русский',
  zh: '中文',
};
