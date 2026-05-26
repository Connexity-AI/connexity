'use server';

import { ConfigService } from '@/client/sdk.gen';

import type {
  ConfigPublic,
  LlmModelsPublic,
  PredefinedToolsPublic,
  SpeechModelsPublic,
  VoicesPublic,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const getAppConfig = async (): Promise<ApiResult<ConfigPublic>> => {
  const apiResponse = await ConfigService.getConfig();
  if (apiResponse.error !== undefined) {
    return { data: undefined, error: apiResponse.error };
  }
  return { data: apiResponse.data, error: undefined };
};

export const getLlmModels = async (): Promise<ApiResult<LlmModelsPublic>> => {
  const apiResponse = await ConfigService.getLlmModels();
  if (apiResponse.error !== undefined) {
    return { data: undefined, error: apiResponse.error };
  }
  return { data: apiResponse.data, error: undefined };
};

export const getPredefinedTools = async (): Promise<ApiResult<PredefinedToolsPublic>> => {
  const apiResponse = await ConfigService.getPredefinedTools();
  if (apiResponse.error !== undefined) {
    return { data: undefined, error: apiResponse.error };
  }
  return { data: apiResponse.data, error: undefined };
};

export const getSttModels = async (): Promise<ApiResult<SpeechModelsPublic>> => {
  const apiResponse = await ConfigService.getSttModels();
  if (apiResponse.error !== undefined) {
    return { data: undefined, error: apiResponse.error };
  }
  return { data: apiResponse.data, error: undefined };
};

export const getTtsModels = async (): Promise<ApiResult<SpeechModelsPublic>> => {
  const apiResponse = await ConfigService.getTtsModels();
  if (apiResponse.error !== undefined) {
    return { data: undefined, error: apiResponse.error };
  }
  return { data: apiResponse.data, error: undefined };
};

export const getTtsVoices = async (
  provider: string,
  model: string
): Promise<ApiResult<VoicesPublic>> => {
  const apiResponse = await ConfigService.getTtsVoices({
    query: { provider, model },
  });
  if (apiResponse.error !== undefined) {
    return { data: undefined, error: apiResponse.error };
  }
  return { data: apiResponse.data, error: undefined };
};
