'use server';

import { CompanyService, UsersService } from '@/client/sdk.gen';

import type {
  CompanyLlmCredentialsPublic,
  CompanyLlmCredentialsUpdate,
  OnboardingStatusPublic,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const getOnboardingStatus = async (): Promise<ApiResult<OnboardingStatusPublic>> => {
  const apiResponse = await UsersService.readOnboardingStatus();
  const { response: _, ...result } = apiResponse;
  return result;
};

export const getLlmCredentials = async (): Promise<ApiResult<CompanyLlmCredentialsPublic>> => {
  const apiResponse = await CompanyService.getLlmCredentials();
  const { response: _, ...result } = apiResponse;
  return result;
};

export const updateLlmCredentials = async (
  body: CompanyLlmCredentialsUpdate
): Promise<ApiResult<CompanyLlmCredentialsPublic>> => {
  const apiResponse = await CompanyService.updateLlmCredentials({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};
