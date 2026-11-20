'use server';

import { cookies } from 'next/headers';
import { revalidatePath } from 'next/cache';

import { TENANT_COOKIE, isValidUuid } from '@/lib/tenant';
import { LOCALE_COOKIE, isLocale } from '@/lib/i18n/config';

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

export async function setActiveTenant(tenantId: string): Promise<void> {
  if (!isValidUuid(tenantId)) {
    throw new Error(`Invalid tenant id: ${tenantId}`);
  }
  cookies().set({
    name: TENANT_COOKIE,
    value: tenantId,
    httpOnly: false,
    sameSite: 'lax',
    path: '/',
    maxAge: ONE_YEAR_SECONDS,
  });
  revalidatePath('/', 'layout');
}

export async function setActiveLocale(locale: string): Promise<void> {
  if (!isLocale(locale)) {
    throw new Error(`Unsupported locale: ${locale}`);
  }
  cookies().set({
    name: LOCALE_COOKIE,
    value: locale,
    httpOnly: false,
    sameSite: 'lax',
    path: '/',
    maxAge: ONE_YEAR_SECONDS,
  });
  revalidatePath('/', 'layout');
}
