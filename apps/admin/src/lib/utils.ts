import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Canonical `cn()` from shadcn/ui: merge Tailwind class names safely.
 *
 * Use this everywhere instead of template-string concatenation so that
 * later utilities reliably override earlier ones (`p-2` then `p-4` → `p-4`).
 */
export function cn(...inputs: readonly ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format an ISO-8601 timestamp into the user's locale. SSR-safe. */
export function formatDateTime(value: string | Date, locale = 'en'): string {
  const date = typeof value === 'string' ? new Date(value) : value;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

/**
 * Currency formatter. Defaults to USD; tenants override per `pricing_zones`.
 *
 * Public utility — used by monetization / invoices pages (planned).
 *
 * @public
 */
export function formatMoney(amount: number, currency = 'USD', locale = 'en'): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}
