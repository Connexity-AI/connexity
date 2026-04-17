'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { updateAgent } from '@/actions/agents';
import { agentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { AgentUpdate } from '@/client/types.gen';
import type {
  AgentFormValues,
  AgentToolValues,
} from '@/app/(app)/(agent)/_schemas/agent-form';

function mapToolToOpenAI(tool: AgentToolValues): Record<string, unknown> {
  const hasEndpoint = tool.url.trim().length > 0;

  const headers = tool.authHeaders.reduce<Record<string, string>>((accumulator, header) => {
    if (header.key.trim()) accumulator[header.key] = header.value;
    return accumulator;
  }, {});

  return {
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: {
        type: 'object',
        properties: Object.fromEntries(
          tool.parameters.map((parameter) => [
            parameter.name,
            { type: parameter.type, description: parameter.description },
          ])
        ),
        required: tool.parameters
          .filter((parameter) => parameter.required)
          .map((parameter) => parameter.name),
      },
    },
    ...(hasEndpoint && {
      platform_config: {
        mode: 'live',
        implementation: {
          type: 'http_webhook',
          url: tool.url,
          method: tool.method,
          headers: Object.keys(headers).length > 0 ? headers : undefined,
          timeout_ms: tool.timeout * 1000,
        },
      },
    }),
  };
}

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
