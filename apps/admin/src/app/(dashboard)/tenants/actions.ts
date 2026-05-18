'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';

import { tenantsApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';

export interface ActionResult {
  readonly ok: boolean;
  readonly message?: string;
}

const createSchema = z.object({
  slug: z.string().regex(/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/, 'slug must be lowercase'),
  display_name: z.record(z.string().min(1), z.string()).refine(
    (v) => Object.keys(v).length > 0,
    'display_name required',
  ),
});

const patchSchema = z.object({
  display_name: z.record(z.string().min(1), z.string()).optional(),
  status: z.enum(['active', 'suspended', 'archived']).optional(),
  plan_tier: z.string().min(1).max(32).optional(),
});

export async function createTenantAction(input: unknown): Promise<ActionResult> {
  const parsed = createSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? 'Invalid payload' };
  }
  try {
    await tenantsApi.createTenant(parsed.data);
    revalidatePath('/tenants');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Create failed' };
  }
}

export async function patchTenantAction(
  slug: string,
  input: unknown,
): Promise<ActionResult> {
  const parsed = patchSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? 'Invalid payload' };
  }
  try {
    await tenantsApi.patchTenant(slug, parsed.data);
    revalidatePath('/tenants');
    revalidatePath(`/tenants/${slug}`);
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Update failed' };
  }
}
