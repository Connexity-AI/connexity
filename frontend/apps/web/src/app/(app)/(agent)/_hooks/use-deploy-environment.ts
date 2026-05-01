'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deployEnvironment } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { DeploymentPublic } from '@/client/types.gen';

interface DeployArgs {
  environmentId: string;
  agentVersion: number;
}

export function useDeployEnvironment(agentId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation<DeploymentPublic, Error, DeployArgs>({
    mutationFn: async ({ environmentId, agentVersion }) => {
      const result = await deployEnvironment(environmentId, { agent_version: agentVersion });
      if (isErrorApiResult(result)) {
        throw new Error(getApiErrorMessage(result.error));
      }
      if (result.data.status === 'failed') {
        throw new Error(result.data.error_message ?? 'Deploy failed');
      }
      return result.data;
    },
    onSettled: (_data, _err, { environmentId }) => {
      void queryClient.invalidateQueries({ queryKey: environmentKeys.list(agentId) });
      void queryClient.invalidateQueries({
        queryKey: environmentKeys.deployments(environmentId),
      });
      void queryClient.invalidateQueries({
        queryKey: environmentKeys.agentDeployments(agentId),
      });
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    data: mutation.data,
    error: mutation.error?.message ?? null,
    reset: mutation.reset,
  };
}
