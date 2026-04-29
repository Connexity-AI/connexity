'use server';

import { ConfigService } from '@/client/sdk.gen';

import type { LlmModelsPublic } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const getLlmModels = async (): Promise<ApiResult<LlmModelsPublic>> => {
  const apiResponse = await ConfigService.getLlmModels();
  if (apiResponse.error !== undefined) {
    return { data: undefined, error: apiResponse.error };
  }
  return { data: apiResponse.data, error: undefined };
};
