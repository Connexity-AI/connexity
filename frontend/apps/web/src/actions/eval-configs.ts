'use server';

import { ConfigService, EvalConfigsService, RunsService } from '@/client/sdk.gen';

import type {
  AvailableMetricsPublic,
  EvalConfigCreate,
  EvalConfigMembersPublic,
  EvalConfigPublic,
  EvalConfigsPublic,
  RunCreate,
  RunPublic,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const listEvalConfigs = async (
  agentId: string,
  skip: number = 0,
  limit: number = 100
): Promise<ApiResult<EvalConfigsPublic>> => {
  const apiResponse = await EvalConfigsService.evalConfigsListEvalConfigs({
    query: { agent_id: agentId, skip, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const getEvalConfig = async (
  evalConfigId: string
): Promise<ApiResult<EvalConfigPublic>> => {
  const apiResponse = await EvalConfigsService.evalConfigsGetEvalConfig({
    path: { eval_config_id: evalConfigId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listEvalConfigMembers = async (
  evalConfigId: string,
  skip: number = 0,
  limit: number = 500
): Promise<ApiResult<EvalConfigMembersPublic>> => {
  const apiResponse = await EvalConfigsService.evalConfigsListTestCasesInConfig({
    path: { eval_config_id: evalConfigId },
    query: { skip, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const createEvalConfig = async (
  body: EvalConfigCreate
): Promise<ApiResult<EvalConfigPublic>> => {
  const apiResponse = await EvalConfigsService.evalConfigsCreateEvalConfig({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listAvailableMetrics = async (): Promise<ApiResult<AvailableMetricsPublic>> => {
  const apiResponse = await ConfigService.getAvailableMetrics();
  const { response: _, ...result } = apiResponse;
  return result;
};

export const createRun = async (
  body: RunCreate,
  autoExecute: boolean = false
): Promise<ApiResult<RunPublic>> => {
  const apiResponse = await RunsService.createRun({
    body,
    query: { auto_execute: autoExecute },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
