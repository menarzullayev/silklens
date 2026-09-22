import { auth } from '@/lib/auth/auth';
import { errorForStatus, NetworkError } from '@/lib/api/errors';

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
 *   5. On 401, attempt a single silent refresh via `/v1/auth/refresh` and
 *      retry once. If that still fails, throw `UnauthorizedError` and the
 *      caller can redirect to `/login`.
 */

const DEFAULT_TIMEOUT_MS = 15_000;

export interface ApiRequest {
  readonly path: string;
  readonly method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  readonly query?: Readonly<
    Record<string, string | number | boolean | undefined | null>
  >;
  readonly body?: unknown;
  readonly headers?: Readonly<Record<string, string>>;
  readonly tenantId?: string;
  readonly signal?: AbortSignal;
  readonly timeoutMs?: number;
  /** Skip Bearer-token injection (e.g. for the public /health probe). */
  readonly anonymous?: boolean;
  /** Pin a specific access token instead of pulling from the session. */
  readonly accessToken?: string;
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
    if (v === undefined || v === null || v === '') continue;
    params.set(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : '';
}

interface RefreshOutcome {
  readonly accessToken: string;
  readonly refreshToken: string;
  readonly expiresIn: number;
}

async function refreshAccessToken(
  refreshToken: string,
): Promise<RefreshOutcome | null> {
  const url = `${resolveBaseUrl().replace(/\/+$/, '')}/v1/auth/refresh`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const body = (await res.json()) as {
      tokens?: { access_token?: string; refresh_token?: string; expires_in?: number };
    };
    const t = body.tokens;
    if (!t?.access_token || !t.refresh_token || !t.expires_in) return null;
    return {
      accessToken: t.access_token,
      refreshToken: t.refresh_token,
      expiresIn: t.expires_in,
    };
  } catch {
    return null;
  }
}

async function executeFetch(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  callerSignal: AbortSignal | undefined,
  path: string,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  if (callerSignal) {
    if (callerSignal.aborted) controller.abort();
    else
      callerSignal.addEventListener('abort', () => controller.abort(), {
        once: true,
      });
  }
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (cause) {
    throw new NetworkError(
      cause instanceof Error ? cause.message : 'Network failure',
      0,
      cause,
      path,
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function apiFetch<T>(req: ApiRequest): Promise<T> {
  const base = resolveBaseUrl();
  const url = `${base.replace(/\/+$/, '')}${req.path}${buildQuery(req.query)}`;

  const baseHeaders = new Headers(req.headers);
  baseHeaders.set('Accept', 'application/json');
  if (req.body !== undefined && !baseHeaders.has('Content-Type')) {
    baseHeaders.set('Content-Type', 'application/json');
  }

  // Bearer injection — server-side only. Client components route through
  // server actions or React Query against server route handlers.
  let accessToken: string | undefined = req.accessToken;
  let refreshToken: string | undefined;
  if (!req.anonymous && typeof window === 'undefined' && !accessToken) {
    const session = await auth();
    accessToken = session?.accessToken;
    refreshToken = session?.refreshToken;
  }
  if (accessToken) baseHeaders.set('Authorization', `Bearer ${accessToken}`);

  const tenantId = req.tenantId ?? process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
  if (tenantId) baseHeaders.set('X-Tenant-Id', tenantId);

  const init: RequestInit = {
    method: req.method ?? 'GET',
    headers: baseHeaders,
    body: req.body === undefined ? undefined : JSON.stringify(req.body),
    cache: 'no-store',
  };

  let response = await executeFetch(
    url,
    init,
    req.timeoutMs ?? DEFAULT_TIMEOUT_MS,
    req.signal,
    req.path,
  );

  // 401 → attempt one silent refresh + retry.
  if (response.status === 401 && refreshToken && !req.anonymous) {
    const refreshed = await refreshAccessToken(refreshToken);
    if (refreshed) {
      const retryHeaders = new Headers(init.headers);
      retryHeaders.set('Authorization', `Bearer ${refreshed.accessToken}`);
      response = await executeFetch(
        url,
        { ...init, headers: retryHeaders },
        req.timeoutMs ?? DEFAULT_TIMEOUT_MS,
        req.signal,
        req.path,
      );
    }
  }

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
    const message = extractDetailMessage(parsed, req.path, response.status);
    throw errorForStatus(response.status, parsed, req.path, message);
  }

  return parsed as T;
}

function extractDetailMessage(
  parsed: unknown,
  path: string,
  status: number,
): string {
  if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
    const detail = (parsed as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const msg = (detail as { message: unknown }).message;
      if (typeof msg === 'string') return msg;
    }
  }
  return `Request to ${path} failed with status ${status}`;
}
