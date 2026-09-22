'use server';

import { revalidatePath } from 'next/cache';

import { tenantsApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import type { BrandingPutInput } from '@/types/api';

export interface ActionResult {
  readonly ok: boolean;
  readonly message?: string;
}

export async function saveBrandingAction(
  slug: string,
  payload: BrandingPutInput,
): Promise<ActionResult> {
  try {
    await tenantsApi.putBranding(slug, payload);
    revalidatePath('/branding');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Save failed' };
  }
}
