import { apiFetch } from './client';
import type { AiChainOut, AiModelOut, AiModelPatchInput } from '@/types/api';

export function listAiModels(): Promise<readonly AiModelOut[]> {
  return apiFetch<readonly AiModelOut[]>({ path: '/v1/ai/models' });
}

export function patchAiModel(
  slug: string,
  input: AiModelPatchInput,
): Promise<AiModelOut> {
  return apiFetch<AiModelOut>({
    path: `/v1/ai/models/${encodeURIComponent(slug)}`,
    method: 'PATCH',
    body: input,
  });
}

export function listAiFallbackChains(): Promise<readonly AiChainOut[]> {
  return apiFetch<readonly AiChainOut[]>({ path: '/v1/ai/fallback-chains' });
}
