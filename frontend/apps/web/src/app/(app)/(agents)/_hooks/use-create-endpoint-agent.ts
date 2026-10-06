'use client';

import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createAgent } from '@/actions/agents';
import { AgentMode, Platform } from '@/client/types.gen';
import { agentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

interface CreateEndpointAgentPayload {
  name: string;
  endpointUrl: string;
}

/** Creates a self-hosted agent that Connexity reaches through its own HTTP endpoint. */
export function useCreateEndpointAgent() {
  const queryClient = useQueryClient();
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: ({ name, endpointUrl }: CreateEndpointAgentPayload) =>
      createAgent({
        name,
        mode: AgentMode.ENDPOINT,
        endpoint_url: endpointUrl,
        platform: Platform.WEBHOOK,
      }),

    onSuccess: (result) => {
      if (isErrorApiResult(result)) return;
      router.push(UrlGenerator.agentEvals(result.data.id));

      queryClient.invalidateQueries({ queryKey: agentKeys.lists });
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
  };
}
