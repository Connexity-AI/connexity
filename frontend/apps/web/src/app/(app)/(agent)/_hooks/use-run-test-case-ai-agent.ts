'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { runTestCaseAiAgent } from '@/actions/test-cases';
import {
  AppServicesTestCaseGeneratorAgentSchemasAgentMode,
  type ConversationTurnInput,
} from '@/client/types.gen';
import { callKeys, testCaseKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

interface RunTestCaseAiAgentInput {
  prompt: string;
  sourceCallId?: string | null;
  transcript?: ConversationTurnInput[] | null;
}

export function useRunTestCaseAiAgent(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ prompt, sourceCallId, transcript }: RunTestCaseAiAgentInput) => {
      const hasTranscript = !!transcript && transcript.length > 0;
      return runTestCaseAiAgent({
        mode: hasTranscript
          ? AppServicesTestCaseGeneratorAgentSchemasAgentMode.FROM_TRANSCRIPT
          : AppServicesTestCaseGeneratorAgentSchemasAgentMode.CREATE,
        user_message: prompt,
        agent_id: agentId,
        persist: true,
        source_call_id: sourceCallId ?? null,
        transcript: hasTranscript ? transcript : null,
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
      queryClient.invalidateQueries({ queryKey: callKeys.all });
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
