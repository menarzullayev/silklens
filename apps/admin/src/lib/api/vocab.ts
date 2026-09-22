import { apiFetch } from './client';
import type { VocabOut } from '@/types/api';

export function getVocab(slug: string): Promise<VocabOut> {
  return apiFetch<VocabOut>({
    path: `/v1/vocab/${encodeURIComponent(slug)}`,
    anonymous: true,
  });
}
