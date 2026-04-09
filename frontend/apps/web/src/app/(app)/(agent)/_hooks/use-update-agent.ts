'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { updateAgent } from '@/actions/agents';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { AgentUpdate, AgentPublic } from '@/client/types.gen';
import type {
  AgentFormValues,
  AgentToolValues,
} from '@/app/(app)/(agent)/_schemas/agent-form';

function mapToolToOpenAI(tool: AgentToolValues): Record<string, unknown> {
  const hasEndpoint = tool.url.trim().length > 0;

  const headers = tool.authHeaders.reduce<Record<string, string>>((acc, h) => {
    if (h.key.trim()) acc[h.key] = h.value;
    return acc;
  }, {});

  return {
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: {
        type: 'object',
        properties: Object.fromEntries(
          tool.parameters.map((p) => [p.name, { type: p.type, description: p.description }])
        ),
        required: tool.parameters.filter((p) => p.required).map((p) => p.name),
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
      const agent = result.data as AgentPublic;
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.setQueryData(['agent', agentId], agent);
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
