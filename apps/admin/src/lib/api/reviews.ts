import { apiFetch } from './client';
import type { ReviewPage } from '@/types/api';

export function listHeritageReviews(
  pubId: string,
  opts: { limit?: number; offset?: number } = {},
): Promise<ReviewPage> {
  return apiFetch<ReviewPage>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}/reviews`,
    query: { limit: opts.limit ?? 20, offset: opts.offset ?? 0 },
    anonymous: true,
  });
}
