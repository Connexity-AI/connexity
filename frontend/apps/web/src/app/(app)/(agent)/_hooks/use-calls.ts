'use client';

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  getCalls,
  markCallSeen,
  refreshCalls,
  type CallQueryFilters,
  type GetCallsResult,
} from '@/actions/calls';
import { callKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function useCalls(agentId: string, filters: CallQueryFilters = {}) {
  return useQuery({
    queryKey: callKeys.list(agentId, filters),
    queryFn: () => getCalls(agentId, filters),
    staleTime: 15 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useRefreshCalls(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const result = await refreshCalls(agentId);
      if (!isSuccessApiResult(result)) {
        throw new Error('Failed to refresh calls');
      }
      return result.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['calls', agentId] });
    },
  });
}

export function useMarkCallSeen(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (callId: string) => {
      const result = await markCallSeen(callId);
      if (!isSuccessApiResult(result)) throw new Error('Failed to mark seen');
      return result.data;
    },
    onMutate: async (callId: string) => {
      await qc.cancelQueries({ queryKey: ['calls', agentId] });
      const snapshots = qc.getQueriesData<GetCallsResult>({ queryKey: ['calls', agentId] });
      qc.setQueriesData<GetCallsResult>({ queryKey: ['calls', agentId] }, (prev) => {
        if (!prev) return prev;
        let changed = false;
        const rows = prev.rows.map((row) => {
          if (row.id !== callId || !row.is_new) return row;
          changed = true;
          return { ...row, is_new: false };
        });
        return changed ? { ...prev, rows } : prev;
      });
      return { snapshots };
    },
    onError: (_err, _callId, context) => {
      context?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
  });
}
