'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { reextractAgentRequirements } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

export function useReextractRequirements(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => reextractAgentRequirements(agentId),
    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      // Status is now `extracting`; the requirements query polls while extracting
      // and will pick up the final result.
      queryClient.invalidateQueries({ queryKey: agentKeys.requirements(agentId) });
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return {
    reextract: mutation.mutate,
    isPending: mutation.isPending,
    error,
  };
}
