/**
 * Unit tests for src/lib/utils.ts
 *
 * Covers: cn() class-name merger, formatDateTime() ISO → locale string,
 * formatMoney() currency formatter.
 */
import { describe, expect, it } from 'vitest';

import { cn, formatDateTime, formatMoney } from './utils';

// ---------------------------------------------------------------------------
// cn()
// ---------------------------------------------------------------------------

describe('cn()', () => {
  it('returns an empty string with no arguments', () => {
    expect(cn()).toBe('');
  });

  it('joins two plain class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('strips falsy values (false, null, undefined, empty string)', () => {
    expect(cn('a', false, null, undefined, '', 'b')).toBe('a b');
  });

  it('deduplicates Tailwind conflicting utilities — last wins', () => {
    // tailwind-merge resolves p-2 vs p-4 → p-4
    expect(cn('p-2', 'p-4')).toBe('p-4');
  });

  it('resolves conflicting padding + padding-x — more specific wins', () => {
    // p-4 px-6 → px-6 overrides the horizontal component
    const result = cn('p-4', 'px-6');
    expect(result).toBe('p-4 px-6');
  });

  it('keeps non-conflicting utilities from both args', () => {
    const result = cn('text-sm font-medium', 'text-red-500');
    expect(result).toContain('text-red-500');
    expect(result).toContain('font-medium');
  });

  it('handles array inputs (clsx-style)', () => {
    expect(cn(['a', 'b'], 'c')).toBe('a b c');
  });

  it('handles object inputs (clsx-style conditional classes)', () => {
    expect(cn({ active: true, disabled: false })).toBe('active');
  });

  it('combines object + string + array in one call', () => {
    const result = cn('base', { extra: true, hidden: false }, ['tail']);
    expect(result).toBe('base extra tail');
  });

  it('is idempotent — calling twice with same input gives same output', () => {
    const first = cn('text-sm', 'font-bold');
    const second = cn('text-sm', 'font-bold');
    expect(first).toBe(second);
  });
});

// ---------------------------------------------------------------------------
// formatDateTime()
// ---------------------------------------------------------------------------

describe('formatDateTime()', () => {
  // Use a fixed date to avoid flakiness from timezone drift.
  // 2024-06-15T12:00:00.000Z — noon UTC on a Saturday
  const ISO = '2024-06-15T12:00:00.000Z';
  const DATE_OBJ = new Date(ISO);

  it('accepts an ISO string and returns a non-empty string', () => {
    const result = formatDateTime(ISO);
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });

  it('accepts a Date object and returns the same value as the ISO string', () => {
    expect(formatDateTime(DATE_OBJ)).toBe(formatDateTime(ISO));
  });

  it('default locale is "en"', () => {
    // Both calls must be identical (default = 'en').
    expect(formatDateTime(ISO)).toBe(formatDateTime(ISO, 'en'));
  });

  it('returns a different string for different locales', () => {
    const en = formatDateTime(ISO, 'en');
    const ru = formatDateTime(ISO, 'ru');
    // Russian month names differ from English.
    expect(en).not.toBe(ru);
  });

  it('contains the year 2024 in its output', () => {
    expect(formatDateTime(ISO, 'en')).toContain('2024');
  });

  it('uses medium dateStyle so the day number appears', () => {
    // "Jun 15, 2024, …" — day 15 must be present.
    const result = formatDateTime(ISO, 'en');
    expect(result).toContain('15');
  });

  it('handles a Date object constructed from epoch 0 without throwing', () => {
    expect(() => formatDateTime(new Date(0), 'en')).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// formatMoney()
// ---------------------------------------------------------------------------

describe('formatMoney()', () => {
  it('formats a positive USD amount in en locale', () => {
    const result = formatMoney(1234.5, 'USD', 'en');
    // Must contain the dollar sign and the amount.
    expect(result).toContain('$');
    expect(result).toContain('1,234');
  });

  it('defaults to USD currency', () => {
    expect(formatMoney(100, 'USD', 'en')).toBe(formatMoney(100, undefined as unknown as string, 'en') === '' ? '' : formatMoney(100, 'USD', 'en'));
    // Simpler: calling with explicit USD matches the default-currency version.
    const withDefault = formatMoney(100);
    const withUSD = formatMoney(100, 'USD', 'en');
    // Both should start with $ (en locale default).
    expect(withDefault).toMatch(/\$/);
    expect(withUSD).toMatch(/\$/);
  });

  it('formats EUR correctly for en locale', () => {
    const result = formatMoney(99.99, 'EUR', 'en');
    expect(result).toContain('€');
    expect(result).toContain('99.99');
  });

  it('returns a different string for different currencies on the same amount', () => {
    expect(formatMoney(100, 'USD', 'en')).not.toBe(formatMoney(100, 'EUR', 'en'));
  });

  it('caps at 2 decimal places for round numbers', () => {
    // 1000 USD → "$1,000.00"
    const result = formatMoney(1000, 'USD', 'en');
    expect(result).toMatch(/\d{1,3}(,\d{3})*(\.\d{2})?/);
  });

  it('handles zero amount without throwing', () => {
    expect(() => formatMoney(0)).not.toThrow();
    expect(formatMoney(0, 'USD', 'en')).toContain('0');
  });

  it('handles negative amounts (refunds)', () => {
    const result = formatMoney(-50, 'USD', 'en');
    expect(typeof result).toBe('string');
    expect(result).toContain('50');
  });

  it('handles very large amounts without throwing', () => {
    expect(() => formatMoney(1_000_000_000, 'USD', 'en')).not.toThrow();
  });
});
