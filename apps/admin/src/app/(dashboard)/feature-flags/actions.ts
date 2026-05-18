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
  enabled: z.boolean(),
  rollout_kind: z.enum([
    'boolean',
    'percentage',
    'user_allowlist',
    'user_denylist',
    'jsonl_rules',
  ]),
  rollout_value: z.record(z.string(), z.unknown()),
  description: z.string().max(512).nullable().optional(),
});

export async function saveFlagAction(input: unknown): Promise<ActionResult> {
  const parsed = schema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? 'Invalid payload' };
  }
  try {
    await systemApi.putFeatureFlag(parsed.data.key, {
      enabled: parsed.data.enabled,
      rollout_kind: parsed.data.rollout_kind,
      rollout_value: parsed.data.rollout_value,
      description: parsed.data.description ?? null,
    });
    revalidatePath('/feature-flags');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Save failed' };
  }
}
