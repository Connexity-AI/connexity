'use server';

import { IntegrationsService } from '@/client/sdk.gen';

import type {
  IntegrationCreate,
  IntegrationPublic,
  IntegrationsPublic,
  RetellAgentSummary,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const createIntegration = async (
  body: IntegrationCreate
): Promise<ApiResult<IntegrationPublic>> => {
  const apiResponse = await IntegrationsService.createIntegration({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listIntegrations = async (
  skip = 0,
  limit = 100
): Promise<ApiResult<IntegrationsPublic>> => {
  const apiResponse = await IntegrationsService.listIntegrations({
    query: { skip, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const deleteIntegration = async (id: string): Promise<ApiResult<void>> => {
  const apiResponse = await IntegrationsService.deleteIntegration({
    path: { integration_id: id },
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<void>;
};

export const testIntegration = async (id: string): Promise<ApiResult<{ message: string }>> => {
  const apiResponse = await IntegrationsService.testIntegration({
    path: { integration_id: id },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listRetellAgents = async (
  integrationId: string
): Promise<ApiResult<RetellAgentSummary[]>> => {
  const apiResponse = await IntegrationsService.listIntegrationAgents({
    path: { integration_id: integrationId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
