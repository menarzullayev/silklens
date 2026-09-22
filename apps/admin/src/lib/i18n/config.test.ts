/**
 * Unit tests for src/lib/i18n/config.ts
 *
 * Covers: LOCALES tuple, DEFAULT_LOCALE, LOCALE_COOKIE constant,
 * isLocale() type guard, LOCALE_LABELS completeness.
 */
import { describe, expect, it } from 'vitest';

import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE,
  LOCALE_LABELS,
  LOCALES,
  isLocale,
} from './config';

// ---------------------------------------------------------------------------
// LOCALES
// ---------------------------------------------------------------------------

describe('LOCALES', () => {
  it('contains exactly 4 launch locales', () => {
    expect(LOCALES).toHaveLength(4);
  });

  it('includes "uz" (Uzbek)', () => {
    expect(LOCALES).toContain('uz');
  });

  it('includes "en" (English)', () => {
    expect(LOCALES).toContain('en');
  });

  it('includes "ru" (Russian)', () => {
    expect(LOCALES).toContain('ru');
  });

  it('includes "zh" (Chinese)', () => {
    expect(LOCALES).toContain('zh');
  });

  it('has no duplicate entries', () => {
    expect(new Set(LOCALES).size).toBe(LOCALES.length);
  });

  it('all entries are lowercase two-letter BCP-47 subtags', () => {
    for (const locale of LOCALES) {
      expect(locale).toMatch(/^[a-z]{2}$/);
    }
  });
});

// ---------------------------------------------------------------------------
// DEFAULT_LOCALE
// ---------------------------------------------------------------------------

describe('DEFAULT_LOCALE', () => {
  it('is a member of LOCALES', () => {
    expect(LOCALES).toContain(DEFAULT_LOCALE);
  });

  it('is "uz" (Uzbek — primary market)', () => {
    expect(DEFAULT_LOCALE).toBe('uz');
  });
});

// ---------------------------------------------------------------------------
// LOCALE_COOKIE
// ---------------------------------------------------------------------------

describe('LOCALE_COOKIE', () => {
  it('is "silklens.locale"', () => {
    expect(LOCALE_COOKIE).toBe('silklens.locale');
  });

  it('is a non-empty string', () => {
    expect(typeof LOCALE_COOKIE).toBe('string');
    expect(LOCALE_COOKIE.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// isLocale()
// ---------------------------------------------------------------------------

describe('isLocale()', () => {
  describe('valid locales', () => {
    it('returns true for "uz"', () => {
      expect(isLocale('uz')).toBe(true);
    });

    it('returns true for "en"', () => {
      expect(isLocale('en')).toBe(true);
    });

    it('returns true for "ru"', () => {
      expect(isLocale('ru')).toBe(true);
    });

    it('returns true for "zh"', () => {
      expect(isLocale('zh')).toBe(true);
    });

    it('returns true for every member of LOCALES', () => {
      for (const locale of LOCALES) {
        expect(isLocale(locale)).toBe(true);
      }
    });
  });

  describe('invalid / unsupported values', () => {
    const invalid = [
      '',
      'fr',
      'de',
      'ar',
      'UZ', // uppercase — locales are lowercase
      'EN',
      'uz-UZ', // full BCP-47 tag (not a plain subtag)
      'english',
      '  ',
      '123',
    ];

    for (const value of invalid) {
      it(`returns false for "${value}"`, () => {
        expect(isLocale(value)).toBe(false);
      });
    }
  });
});

// ---------------------------------------------------------------------------
// LOCALE_LABELS
// ---------------------------------------------------------------------------

describe('LOCALE_LABELS', () => {
  it('has a label for every locale in LOCALES', () => {
    for (const locale of LOCALES) {
      expect(LOCALE_LABELS[locale]).toBeDefined();
    }
  });

  it('all labels are non-empty strings', () => {
    for (const locale of LOCALES) {
      expect(typeof LOCALE_LABELS[locale]).toBe('string');
      expect(LOCALE_LABELS[locale].length).toBeGreaterThan(0);
    }
  });

  it('"uz" label is the Uzbek native name', () => {
    expect(LOCALE_LABELS['uz']).toBe("O'zbek");
  });

  it('"en" label is "English"', () => {
    expect(LOCALE_LABELS['en']).toBe('English');
  });

  it('"ru" label is the Russian native name', () => {
    expect(LOCALE_LABELS['ru']).toBe('Русский');
  });

  it('"zh" label is the Chinese native name', () => {
    expect(LOCALE_LABELS['zh']).toBe('中文');
  });

  it('has no extra keys beyond LOCALES', () => {
    expect(Object.keys(LOCALE_LABELS)).toHaveLength(LOCALES.length);
  });
});
