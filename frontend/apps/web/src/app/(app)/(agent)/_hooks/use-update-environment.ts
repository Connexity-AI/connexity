'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { updateEnvironment } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { EnvironmentUpdate } from '@/client/types.gen';

interface UpdateEnvironmentVariables {
  environmentId: string;
  body: EnvironmentUpdate;
}

export function useUpdateEnvironment(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ environmentId, body }: UpdateEnvironmentVariables) => {
      const result = await updateEnvironment(environmentId, body);
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      return result.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: environmentKeys.list(agentId) });
      void queryClient.invalidateQueries({ queryKey: environmentKeys.agentDeployments(agentId) });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error?.message ?? null,
  };
}
