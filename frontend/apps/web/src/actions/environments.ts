'use server';

import { EnvironmentsService } from '@/client/sdk.gen';

import type { EnvironmentCreate, EnvironmentPublic, EnvironmentsPublic } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const createEnvironment = async (
  body: EnvironmentCreate
): Promise<ApiResult<EnvironmentPublic>> => {
  const apiResponse = await EnvironmentsService.createEnvironment({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listEnvironments = async (
  agentId: string
): Promise<ApiResult<EnvironmentsPublic>> => {
  const apiResponse = await EnvironmentsService.listEnvironments({
    query: { agent_id: agentId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const deleteEnvironment = async (id: string): Promise<ApiResult<void>> => {
  const apiResponse = await EnvironmentsService.deleteEnvironment({
    path: { environment_id: id },
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<void>;
};
