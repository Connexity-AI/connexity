'use server';

import { RunsService, TestCaseResultsService } from '@/client/sdk.gen';

import type {
  Message,
  RunPublic,
  RunsPublic,
  RunStatus,
  TestCaseResultsPublic,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export interface ListRunsOptions {
  skip?: number;
  limit?: number;
  agentVersion?: number | null;
  evalConfigId?: string | null;
  status?: RunStatus | null;
}

export const listRuns = async (
  agentId: string,
  opts: ListRunsOptions = {}
): Promise<ApiResult<RunsPublic>> => {
  const { skip = 0, limit = 200, agentVersion, evalConfigId, status } = opts;
  const apiResponse = await RunsService.listRuns({
    query: {
      agent_id: agentId,
      skip,
      limit,
      agent_version: agentVersion,
      eval_config_id: evalConfigId,
      status,
    },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const getRun = async (runId: string): Promise<ApiResult<RunPublic>> => {
  const apiResponse = await RunsService.getRun({ path: { run_id: runId } });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const deleteRun = async (runId: string): Promise<ApiResult<Message>> => {
  const apiResponse = await RunsService.deleteRun({ path: { run_id: runId } });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listTestCaseResultsByRun = async (
  runId: string,
  limit: number = 500
): Promise<ApiResult<TestCaseResultsPublic>> => {
  const apiResponse = await TestCaseResultsService.testCaseResultsListTestCaseResults({
    query: { run_id: runId, skip: 0, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
