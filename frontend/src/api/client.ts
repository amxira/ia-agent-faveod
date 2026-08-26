// Thin typed client for the Faveod REST API.
// Base URL: VITE_API_BASE (default `/api`, proxied by the Vite dev server).

import type {
  AgentOptions,
  ChatResponse,
  ListResponse,
  NotificationsResult,
  Partner,
  ITEvent,
  Lead,
  RunResult,
  SavedResponse,
  SaveResult,
  Summary,
  Tender,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      headers: init?.body
        ? { 'Content-Type': 'application/json', ...(init.headers ?? {}) }
        : init?.headers,
      ...init,
    });
  } catch {
    throw new ApiError(0, 'API inaccessible — is the backend running on port 8000 ?');
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

function qs(params?: Record<string, string | number | boolean | undefined | null>): string {
  if (!params) return '';
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '' && v !== false) {
      search.set(k, String(v));
    }
  }
  const s = search.toString();
  return s ? `?${s}` : '';
}

export const api = {
  base: API_BASE,

  // system
  health: () => request<{ status: string }>('/health'),
  options: () => request<AgentOptions>('/agents/options'),

  // data
  summary: () => request<Summary>('/summary'),
  tenders: (p?: Record<string, string | number | boolean | undefined | null>) =>
    request<ListResponse<Tender>>(`/tenders${qs(p)}`),
  tender: (id: string) => request<Tender>(`/tenders/${encodeURIComponent(id)}`),
  partners: (p?: Record<string, string | number | boolean | undefined | null>) =>
    request<ListResponse<Partner>>(`/partners${qs(p)}`),
  partner: (id: string) => request<Partner>(`/partners/${encodeURIComponent(id)}`),
  events: (p?: Record<string, string | number | boolean | undefined | null>) =>
    request<ListResponse<ITEvent>>(`/events${qs(p)}`),
  event: (id: string) => request<ITEvent>(`/events/${encodeURIComponent(id)}`),
  leads: (p?: Record<string, string | number | boolean | undefined | null>) =>
    request<ListResponse<Lead>>(`/leads${qs(p)}`),
  lead: (id: string) => request<Lead>(`/leads/${encodeURIComponent(id)}`),

  // favorites
  saved: () => request<SavedResponse>('/saved'),
  saveItem: (kind: string, itemId: string) =>
    request<SaveResult>(`/saved/${kind}/${encodeURIComponent(itemId)}`, { method: 'POST' }),
  unsaveItem: (kind: string, itemId: string) =>
    request<SaveResult>(`/saved/${kind}/${encodeURIComponent(itemId)}`, { method: 'DELETE' }),

  // actions
  runTenders: (body: { sources?: string[]; recent_days?: number; limit?: number }) =>
    request<RunResult>('/run/tenders', { method: 'POST', body: JSON.stringify(body) }),
  runPartners: (body: { source?: string; countries?: string[]; limit?: number }) =>
    request<RunResult>('/run/partners', { method: 'POST', body: JSON.stringify(body) }),
  runEvents: (body: { source?: string; countries?: string[]; upcoming_days?: number; limit?: number }) =>
    request<RunResult>('/run/events', { method: 'POST', body: JSON.stringify(body) }),
  notificationsCheck: (body: { threshold?: number; dry_run?: boolean; reset?: boolean }) =>
    request<NotificationsResult>('/notifications/check', { method: 'POST', body: JSON.stringify(body) }),

  // chat
  chat: (body: { message: string; session_id?: string; max_steps?: number }) =>
    request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify(body) }),
  resetChat: (sessionId: string) =>
    request<{ ok: boolean }>(`/chat/${encodeURIComponent(sessionId)}`, { method: 'DELETE' }),
};
