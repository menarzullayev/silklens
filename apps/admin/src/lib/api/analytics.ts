import { apiFetch } from './client';
import type { HeritagePage } from '@/types/api';

// --- Traction / investor KPI snapshot ----------------------------------------

export interface KpiSnapshot {
  readonly month: string;
  readonly mau?: number;
  readonly arr_usd?: number;
  readonly heritage_count?: number;
}

export interface TractionData {
  readonly mau?: number;
  readonly heritage_count?: number;
  readonly arr_usd?: number;
  readonly total_users?: number;
  readonly verified_users?: number;
  readonly heritage_views?: number;
  readonly ai_requests?: number;
  readonly kpi_snapshots?: readonly KpiSnapshot[];
  readonly [key: string]: unknown;
}

export function getTractionData(): Promise<TractionData> {
  return apiFetch<TractionData>({ path: '/v1/investors/traction' });
}

// --- Recent heritage activity (last 5 created/modified entries) --------------

export function getRecentHeritage(limit = 5): Promise<HeritagePage> {
  return apiFetch<HeritagePage>({
    path: '/v1/heritage',
    query: { limit, offset: 0 },
    anonymous: true,
  });
}
