import { auth } from '@/lib/auth/auth';
import {
  errorForStatus,
  NetworkError,
} from '@/lib/api/errors';

/**
 * Typed fetch wrapper for the SilkLens FastAPI backend.
 *
 * Responsibilities:
 *   1. Resolve the base URL (server-side uses `API_INTERNAL_URL`; browser uses
 *      `NEXT_PUBLIC_API_URL`).
 *   2. Inject the NextAuth Bearer token when called from a Server Component
 *      / Route Handler / Server Action. Client Components should use the
 *      React Query layer which proxies through `/api/...` routes.
 *   3. Attach `X-Tenant-Id` so RLS policies in Postgres bind to the correct
 *      tenant (multi-tenant per Project-Decisions §50, architecture §06.3.1).
 *   4. Normalise non-2xx into the `ApiError` hierarchy in `./errors.ts`.
 */

const DEFAULT_TIMEOUT_MS = 15_000;

export interface ApiRequest {
  readonly path: string;
  readonly method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  readonly query?: Readonly<Record<string, string | number | boolean | undefined>>;
  readonly body?: unknown;
  readonly headers?: Readonly<Record<string, string>>;
  readonly tenantId?: string;
  readonly signal?: AbortSignal;
  readonly timeoutMs?: number;
  /** Skip Bearer-token injection (e.g. for the public /health probe). */
  readonly anonymous?: boolean;
}

function resolveBaseUrl(): string {
  if (typeof window === 'undefined') {
    return process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL;
  }
  return process.env.NEXT_PUBLIC_API_URL;
}

function buildQuery(query: ApiRequest['query']): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined) continue;
    params.set(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : '';
}

export async function apiFetch<T>(req: ApiRequest): Promise<T> {
  const base = resolveBaseUrl();
  const url = `${base.replace(/\/+$/, '')}${req.path}${buildQuery(req.query)}`;

  const headers = new Headers(req.headers);
  headers.set('Accept', 'application/json');
  if (req.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Bearer injection — only on the server, where the NextAuth session is reachable.
  if (!req.anonymous && typeof window === 'undefined') {
    const session = await auth();
    const token = session?.accessToken;
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const tenantId = req.tenantId ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
  if (tenantId) headers.set('X-Tenant-Id', tenantId);

  const controller = new AbortController();
  const timeout = setTimeout(() => {
    controller.abort();
  }, req.timeoutMs ?? DEFAULT_TIMEOUT_MS);

  // Combine caller's AbortSignal with our timeout.
  if (req.signal) {
    if (req.signal.aborted) controller.abort();
    else req.signal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: req.method ?? 'GET',
      headers,
      body: req.body === undefined ? undefined : JSON.stringify(req.body),
      signal: controller.signal,
      cache: 'no-store',
    });
  } catch (cause) {
    clearTimeout(timeout);
    throw new NetworkError(
      cause instanceof Error ? cause.message : 'Network failure',
      0,
      cause,
      req.path,
    );
  }
  clearTimeout(timeout);

  // 204 / 205 — no body to parse.
  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  const text = await response.text();
  let parsed: unknown = null;
  if (text.length > 0) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!response.ok) {
    const message =
      (parsed && typeof parsed === 'object' && 'detail' in parsed
        ? String((parsed as { detail: unknown }).detail)
        : null) ?? `Request to ${req.path} failed with status ${response.status}`;
    throw errorForStatus(response.status, parsed, req.path, message);
  }

  return parsed as T;
}
