'use client';

import { useMutation } from '@tanstack/react-query';

import { runTestCaseAiAgent } from '@/actions/test-cases';
import { AppServicesTestCaseGeneratorInteractiveSchemasAgentMode } from '@/client/types.gen';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

interface EditTestCaseAiAgentInput {
  testCaseId: string;
  prompt: string;
}

export function useEditTestCaseAiAgent(agentId: string) {
  const mutation = useMutation({
    mutationFn: async ({ testCaseId, prompt }: EditTestCaseAiAgentInput) => {
      return runTestCaseAiAgent({
        mode: AppServicesTestCaseGeneratorInteractiveSchemasAgentMode.EDIT,
        agent_id: agentId,
        test_case_id: testCaseId,
        user_message: prompt,
        persist: false,
      });
    },

    onError: (error) => {
      console.error('[ai-tc-edit] mutation error', error);
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return {
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error,
    reset: mutation.reset,
  };
}
