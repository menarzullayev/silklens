'use server';

import { revalidatePath } from 'next/cache';

import { moderationApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';

export interface ActionResult {
  readonly ok: boolean;
  readonly message?: string;
}

export async function approveHeritageAction(
  pubId: string,
  comment?: string,
): Promise<ActionResult> {
  try {
    await moderationApi.moderateHeritage(pubId, 'approve', comment);
    revalidatePath('/moderation');
    revalidatePath('/heritage');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Approve failed' };
  }
}

export async function rejectHeritageAction(
  pubId: string,
  comment?: string,
): Promise<ActionResult> {
  try {
    await moderationApi.moderateHeritage(pubId, 'reject', comment);
    revalidatePath('/moderation');
    revalidatePath('/heritage');
    return { ok: true };
  } catch (cause) {
    if (cause instanceof ApiError) return { ok: false, message: cause.message };
    return { ok: false, message: 'Reject failed' };
  }
}
