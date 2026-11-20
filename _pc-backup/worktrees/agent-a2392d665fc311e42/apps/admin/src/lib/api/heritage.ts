import { apiFetch } from './client';
import type {
  HeritageCreate,
  HeritageOut,
  HeritagePage,
  HeritagePatch,
  HeritageRevisionPage,
  HeritageAlias,
  HeritageTransition,
} from '@/types/api';

export interface HeritageListFilters {
  readonly kind?: string;
  readonly country?: string;
  readonly status?: string;
  readonly search?: string;
  readonly limit?: number;
  readonly offset?: number;
}

export function listHeritage(filters: HeritageListFilters = {}): Promise<HeritagePage> {
  return apiFetch<HeritagePage>({
    path: '/v1/heritage',
    query: {
      kind: filters.kind,
      country: filters.country,
      status: filters.status,
      search: filters.search,
      limit: filters.limit ?? 20,
      offset: filters.offset ?? 0,
    },
    anonymous: true,
  });
}

export function getHeritage(pubId: string): Promise<HeritageOut> {
  return apiFetch<HeritageOut>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}`,
    anonymous: true,
  });
}

export function createHeritage(payload: HeritageCreate): Promise<HeritageOut> {
  return apiFetch<HeritageOut>({
    path: '/v1/heritage',
    method: 'POST',
    body: payload,
  });
}

export function patchHeritage(
  pubId: string,
  payload: HeritagePatch,
): Promise<HeritageOut> {
  return apiFetch<HeritageOut>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}`,
    method: 'PATCH',
    body: payload,
  });
}

export function deleteHeritage(pubId: string): Promise<void> {
  return apiFetch<void>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}`,
    method: 'DELETE',
  });
}

export function addHeritageAlias(
  pubId: string,
  payload: {
    alias: string;
    language_tag: string;
    kind?: string;
    confidence?: number;
    script?: string | null;
    source?: string | null;
  },
): Promise<HeritageAlias> {
  return apiFetch<HeritageAlias>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}/aliases`,
    method: 'POST',
    body: payload,
  });
}

export function listHeritageRevisions(
  pubId: string,
  opts: { limit?: number; offset?: number } = {},
): Promise<HeritageRevisionPage> {
  return apiFetch<HeritageRevisionPage>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}/revisions`,
    query: { limit: opts.limit ?? 20, offset: opts.offset ?? 0 },
  });
}

export function transitionHeritage(
  pubId: string,
  action: HeritageTransition,
  comment?: string,
): Promise<HeritageOut> {
  return apiFetch<HeritageOut>({
    path: `/v1/heritage/${encodeURIComponent(pubId)}/transitions`,
    method: 'POST',
    body: { action, ...(comment ? { comment } : {}) },
  });
}
