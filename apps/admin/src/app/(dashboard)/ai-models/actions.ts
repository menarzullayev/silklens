'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';

import { aiApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';

export interface ActionResult {
  readonly ok: boolean;
  readonly message?: string;
}

const schema = z.object({
  slug: z.string().min(1).max(128),
  is_enabled: z.boolean().optional(),
  sort_order: z.number().int().min(0).max(10_000).optional(),
});

export async function patchAiModelAction(input: unknown): Promise<ActionResult> {
  const parsed = schema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? 'Invalid payload' };
  }
  try {
    await aiApi.patchAiModel(parsed.data.slug, {
      is_enabled: parsed.data.is_enabled,
      sort_order: parsed.data.sort_order,
    });
    revalidatePath('/ai-models');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Save failed' };
  }
}
