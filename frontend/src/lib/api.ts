/** API 客户端 */
import useSWR from 'swr';

const API_BASE = '/api';

function getAuthHeader(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || new URLSearchParams(window.location.search).get('token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const fetcher = (url: string) => fetch(`${API_BASE}${url}`, { headers: getAuthHeader() }).then(r => {
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
});

export function useAPI<T>(path: string | null) {
  return useSWR<T>(path, fetcher);
}

export function fmtMoney(v: number | null | undefined): string {
  if (v == null) return '-';
  const abs = Math.abs(v);
  if (abs >= 1e8) return `¥${(v / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `¥${(v / 1e4).toFixed(1)}万`;
  return `¥${Math.round(v).toLocaleString()}`;
}

export function fmtNum(v: number | null | undefined): string {
  return v == null ? '-' : Math.round(v).toLocaleString();
}

/** 产品系列标准配色（与后端 CAT_TO_SERIES 对应） */
export const SERIES_COLORS: Record<string, string> = {
  PPC: '#15803d', TPC: '#3b82f6', PDA: '#f59e0b', PC: '#8b5cf6',
  IPC: '#ef4444', PDS: '#06b6d4', '配件': '#94a3b8', '外购品': '#a855f7',
};

export function fmtWan(v: number | null | undefined, digits = 1): string {
  if (v == null) return '-';
  return `${(v / 10000).toFixed(digits)}万`;
}
