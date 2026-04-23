'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { runKeys, testCaseResultKeys } from '@/constants/query-keys';
import { UrlGenerator } from '@/common/url-generator/url-generator';

const TERMINAL_EVENTS = [
  'run_completed',
  'run_failed',
  'run_cancelled',
  'stream_closed',
] as const;

interface UseRunStreamArgs {
  runId: string;
  agentId: string;
  enabled: boolean;
}

export function useRunStream({ runId, agentId, enabled }: UseRunStreamArgs) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) return;

    const url = `${UrlGenerator.apiClientProxy()}api/v1/runs/${runId}/stream`;
    const source = new EventSource(url, { withCredentials: true });

    const refetch = () => {
      queryClient.invalidateQueries({ queryKey: runKeys.list(agentId) });
      queryClient.invalidateQueries({ queryKey: runKeys.detail(runId) });
      queryClient.invalidateQueries({ queryKey: testCaseResultKeys.byRun(runId) });
    };

    const handleTerminal = () => {
      refetch();
      source.close();
    };

    TERMINAL_EVENTS.forEach((name) => source.addEventListener(name, handleTerminal));

    source.addEventListener('snapshot', (event) => {
      try {
        const parsed = JSON.parse((event as MessageEvent).data) as { status?: string };
        if (parsed.status && parsed.status !== 'pending' && parsed.status !== 'running') {
          refetch();
        }
      } catch {
        // ignore malformed snapshot payloads
      }
    });

    source.onerror = () => {
      source.close();
    };

    return () => {
      TERMINAL_EVENTS.forEach((name) => source.removeEventListener(name, handleTerminal));
      source.close();
    };
  }, [enabled, runId, agentId, queryClient]);
}
