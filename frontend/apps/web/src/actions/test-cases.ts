'use server';

import { TestCasesService } from '@/client/sdk.gen';

import type { GenerateRequest, GenerateResult, TestCasesPublic } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const listTestCases = async (
  agentId: string,
  skip: number = 0,
  limit: number = 100
): Promise<ApiResult<TestCasesPublic>> => {
  const apiResponse = await TestCasesService.testCasesListTestCases({
    query: { agent_id: agentId, skip, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const generateTestCases = async (
  body: GenerateRequest
): Promise<ApiResult<GenerateResult>> => {
  const apiResponse = await TestCasesService.testCasesGenerateTestCasesEndpoint({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};
