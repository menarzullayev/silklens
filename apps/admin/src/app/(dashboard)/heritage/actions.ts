'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';

import { heritageApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import type { HeritageStatus, HeritageTransition } from '@/types/api';

export interface ActionResult {
  readonly ok: boolean;
  readonly message?: string;
}

const localeRecord = z.record(z.string().min(1), z.string());

const createSchema = z.object({
  kind_slug: z.string().min(2),
  name: localeRecord.refine((v) => Object.keys(v).length > 0, 'name required'),
  summary_md: localeRecord.optional(),
  description_md: localeRecord.optional(),
  tags: z.array(z.string()).optional(),
  country_code: z
    .string()
    .length(2)
    .transform((s) => s.toUpperCase())
    .optional()
    .or(z.literal('').transform(() => undefined)),
  latitude: z.number().min(-90).max(90).optional().nullable(),
  longitude: z.number().min(-180).max(180).optional().nullable(),
  period_start_year: z.number().int().optional().nullable(),
  period_end_year: z.number().int().optional().nullable(),
  unesco_inscription_year: z.number().int().optional().nullable(),
  status: z
    .enum(['draft', 'review', 'published', 'archived', 'rejected'])
    .default('draft'),
});

const patchSchema = createSchema.partial();

export async function createHeritageAction(input: unknown): Promise<ActionResult> {
  const parsed = createSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? 'Invalid payload' };
  }
  let pubId: string;
  try {
    const created = await heritageApi.createHeritage(parsed.data);
    pubId = created.pub_id;
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Create failed' };
  }
  revalidatePath('/heritage');
  // `redirect` throws an internal error that Next.js intercepts — leave it
  // outside the try/catch so we don't swallow it.
  redirect(`/heritage/${pubId}`);
}

export async function patchHeritageAction(
  pubId: string,
  input: unknown,
): Promise<ActionResult> {
  const parsed = patchSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? 'Invalid payload' };
  }
  try {
    await heritageApi.patchHeritage(pubId, parsed.data);
    revalidatePath(`/heritage/${pubId}`);
    revalidatePath('/heritage');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Update failed' };
  }
}

export async function deleteHeritageAction(pubId: string): Promise<ActionResult> {
  try {
    await heritageApi.deleteHeritage(pubId);
    revalidatePath('/heritage');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Delete failed' };
  }
}

export async function transitionHeritageAction(
  pubId: string,
  action: HeritageTransition,
  comment?: string,
): Promise<ActionResult> {
  try {
    await heritageApi.transitionHeritage(pubId, action, comment);
    revalidatePath(`/heritage/${pubId}`);
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Transition failed' };
  }
}

export async function addAliasAction(
  pubId: string,
  payload: {
    alias: string;
    language_tag: string;
    kind?: string;
    confidence?: number;
    script?: string | null;
    source?: string | null;
  },
): Promise<ActionResult> {
  try {
    await heritageApi.addHeritageAlias(pubId, payload);
    revalidatePath(`/heritage/${pubId}`);
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Alias create failed' };
  }
}

// Helper for shaping the `status` patch only.
export async function setHeritageStatusAction(
  pubId: string,
  status: HeritageStatus,
): Promise<ActionResult> {
  return patchHeritageAction(pubId, { status });
}
