'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { runTestCaseAiAgent } from '@/actions/test-cases';
import { AppServicesTestCaseGeneratorAgentSchemasAgentMode } from '@/client/types.gen';
import { testCaseKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

interface RunTestCaseAiAgentInput {
  prompt: string;
}

export function useRunTestCaseAiAgent(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ prompt }: RunTestCaseAiAgentInput) => {
      return runTestCaseAiAgent({
        mode: AppServicesTestCaseGeneratorAgentSchemasAgentMode.CREATE,
        user_message: prompt,
        agent_id: agentId,
        persist: true,
      });
    },

    onError: (error) => {
      console.error('[ai-tc] mutation error', error);
    },

    onSettled: (data) => {
      if (data && isErrorApiResult(data)) {
        console.error('[ai-tc] API error', data.error);
      }
      queryClient.invalidateQueries({ queryKey: testCaseKeys.list(agentId) });
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return {
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error,
    reset: mutation.reset,
  };
}
