'use server';

import { EnvironmentsService } from '@/client/sdk.gen';

import type {
  DeploymentCreate,
  DeploymentPublic,
  DeploymentsPublic,
  EnvironmentCreate,
  EnvironmentPublic,
  EnvironmentsPublic,
  RetellAgentVersion,
} from '@/client/types.gen';
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

export const deployEnvironment = async (
  environmentId: string,
  body: DeploymentCreate
): Promise<ApiResult<DeploymentPublic>> => {
  const apiResponse = await EnvironmentsService.deployEnvironment({
    path: { environment_id: environmentId },
    body,
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listEnvironmentDeployments = async (
  environmentId: string
): Promise<ApiResult<DeploymentsPublic>> => {
  const apiResponse = await EnvironmentsService.listEnvironmentDeployments({
    path: { environment_id: environmentId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listAgentDeployments = async (
  agentId: string
): Promise<ApiResult<DeploymentsPublic>> => {
  const apiResponse = await EnvironmentsService.listAgentDeployments({
    query: { agent_id: agentId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listEnvironmentRetellVersions = async (
  environmentId: string
): Promise<ApiResult<RetellAgentVersion[]>> => {
  const apiResponse = await EnvironmentsService.listEnvironmentRetellVersions({
    path: { environment_id: environmentId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
