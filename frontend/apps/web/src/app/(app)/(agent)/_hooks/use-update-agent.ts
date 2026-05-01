'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { updateAgent } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { AgentUpdate } from '@/client/types.gen';
import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import { mapToolToOpenAI } from '@/app/(app)/(agent)/_utils/map-tool-to-openai';

export function useUpdateAgent(agentId: string, agentName: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: AgentFormValues) => {
      const body: AgentUpdate = {
        name: agentName,
        system_prompt: data.prompt,
        agent_model: data.model,
        agent_provider: data.provider,
        tools: data.tools.length > 0 ? data.tools.map(mapToolToOpenAI) : undefined,
      };
      return updateAgent(agentId, body);
    },
    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      queryClient.invalidateQueries({ queryKey: agentKeys.lists });
      queryClient.setQueryData(agentKeys.detail(agentId), result.data);
    },
  });

  const error =
    mutation.data && isErrorApiResult(mutation.data)
      ? getApiErrorMessage(mutation.data.error)
      : null;

  return {
    mutate: mutation.mutate,
    isPending: mutation.isPending,
    error,
  };
}
