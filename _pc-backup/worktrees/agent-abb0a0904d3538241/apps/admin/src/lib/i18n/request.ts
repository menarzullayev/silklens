import { cookies } from 'next/headers';
import { getRequestConfig } from 'next-intl/server';

import { DEFAULT_LOCALE, LOCALE_COOKIE, isLocale } from './config';

/**
 * next-intl request config — resolves the active locale per request from the
 * `silklens.locale` cookie and loads the matching message catalogue.
 *
 * Catalogues live under `src/messages/<locale>.json`. Adding a locale is just
 * dropping a file and updating `LOCALES` in `./config.ts`.
 */
export default getRequestConfig(async () => {
  const cookieValue = cookies().get(LOCALE_COOKIE)?.value;
  const locale = cookieValue && isLocale(cookieValue) ? cookieValue : DEFAULT_LOCALE;
  const messages = (await import(`../../messages/${locale}.json`)) as {
    default: Record<string, unknown>;
  };

  return {
    locale,
    messages: messages.default,
    timeZone: 'UTC',
  };
});
