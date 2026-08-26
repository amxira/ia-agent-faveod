// Server-state hooks (TanStack Query) wrapping the API client.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api/client';

export const savedKeys = {
  all: ['saved'] as const,
  one: (kind: string, id: string) => ['saved', kind, id] as const,
};

export const useHealth = () =>
  useQuery({ queryKey: ['health'], queryFn: api.health, retry: 1, staleTime: 30_000 });

export const useOptions = () =>
  useQuery({ queryKey: ['options'], queryFn: api.options, staleTime: Infinity });

export const useSummary = (enabled = true) =>
  useQuery({ queryKey: ['summary'], queryFn: api.summary, enabled });

export const useTenders = (params?: Record<string, string | number | boolean | undefined>) =>
  useQuery({ queryKey: ['tenders', params], queryFn: () => api.tenders(params), staleTime: 30_000 });

export const useTender = (id: string | null) =>
  useQuery({
    queryKey: ['tender', id],
    queryFn: () => api.tender(id as string),
    enabled: !!id,
  });

export const usePartners = (params?: Record<string, string | number | boolean | undefined>) =>
  useQuery({ queryKey: ['partners', params], queryFn: () => api.partners(params), staleTime: 30_000 });

export const usePartner = (id: string | null) =>
  useQuery({
    queryKey: ['partner', id],
    queryFn: () => api.partner(id as string),
    enabled: !!id,
  });

export const useEvents = (params?: Record<string, string | number | boolean | undefined>) =>
  useQuery({ queryKey: ['events', params], queryFn: () => api.events(params), staleTime: 30_000 });

export const useLeads = (params?: Record<string, string | number | boolean | undefined>) =>
  useQuery({ queryKey: ['leads', params], queryFn: () => api.leads(params), staleTime: 30_000 });

export const useLead = (id: string | null) =>
  useQuery({ queryKey: ['lead', id], queryFn: () => api.lead(id as string), enabled: !!id });

export const useSaved = () =>
  useQuery({ queryKey: savedKeys.all, queryFn: api.saved, staleTime: 10_000 });

export function useSaveItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, id }: { kind: string; id: string }) => api.saveItem(kind, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: savedKeys.all }),
  });
}

export function useUnsaveItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, id }: { kind: string; id: string }) => api.unsaveItem(kind, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: savedKeys.all }),
  });
}

export function useRunAgent() {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({
      agent,
      body,
    }: {
      agent: 'tenders' | 'partners' | 'events';
      body: Record<string, unknown>;
    }) => {
      if (agent === 'tenders') return api.runTenders(body as never);
      if (agent === 'partners') return api.runPartners(body as never);
      return api.runEvents(body as never);
    },
    onSuccess: () => {
      // Data feeds changed after an agent run.
      void qc.invalidateQueries({ queryKey: ['summary'] });
      void qc.invalidateQueries({ queryKey: ['tenders'] });
      void qc.invalidateQueries({ queryKey: ['partners'] });
      void qc.invalidateQueries({ queryKey: ['events'] });
      void qc.invalidateQueries({ queryKey: ['leads'] });
    },
  });
  return mutation;
}

export function useNotifications() {
  return useMutation({
    mutationFn: (body: { threshold?: number; dry_run?: boolean; reset?: boolean }) =>
      api.notificationsCheck(body),
  });
}

export function useChat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { message: string; session_id?: string; max_steps?: number }) =>
      api.chat(body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['summary'] }),
  });
}

export function useResetChat() {
  return useMutation({
    mutationFn: (sessionId: string) => api.resetChat(sessionId),
  });
}
