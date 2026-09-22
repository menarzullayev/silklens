'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';

import { systemApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';

export interface ActionResult {
  readonly ok: boolean;
  readonly message?: string;
}

const schema = z.object({
  key: z.string().min(2).max(128),
  value: z.unknown().transform((v) => v ?? null),
  value_type: z.enum(['string', 'int', 'float', 'bool', 'json', 'duration', 'color', 'url']),
  scope: z.enum(['tenant', 'global', 'user_overrideable']).default('tenant'),
  description: z.string().max(512).nullable().optional(),
  is_secret: z.boolean().optional(),
});

export async function saveSystemSettingAction(input: unknown): Promise<ActionResult> {
  const parsed = schema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? 'Invalid payload' };
  }
  try {
    await systemApi.putSystemSetting(parsed.data);
    revalidatePath('/settings');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Save failed' };
  }
}
