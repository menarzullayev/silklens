import { apiFetch } from './client';
import type { HeritagePage, HeritageOut, HeritageTransition } from '@/types/api';

/**
 * Fetch heritage objects currently in "review" status — these are the items
 * in the moderation queue awaiting approve/reject.
 */
export function getModerationQueue(params?: {
  limit?: number;
  offset?: number;
}): Promise<HeritagePage> {
  return apiFetch<HeritagePage>({
    path: '/v1/heritage',
    query: {
      status: 'review',
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0,
    },
    anonymous: true,
  });
}

/**
 * Transition a heritage object (approve → published, reject → rejected).
 * Requires `heritage:moderate` permission on the backend.
 */
export function moderateHeritage(
  pubId: string,
  action: Extract<HeritageTransition, 'approve' | 'reject'>,
  comment?: string,
): Promise<HeritageOut> {
  return apiFetch<HeritageOut>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}/transitions`,
    method: 'POST',
    body: { action, ...(comment ? { comment } : {}) },
  });
}
