'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { syncAgentFlow } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

export function useSyncAgentFlow(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => syncAgentFlow(agentId),
    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      // A new version was published with a fresh agent_metadata snapshot:
      // refresh the agent detail, version list, requirements (now re-
      // extracting), and the staleness check so the banner clears.
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.versions(agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.requirements(agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.flowStaleness(agentId) });
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return {
    sync: mutation.mutate,
    isPending: mutation.isPending,
    error,
  };
}
