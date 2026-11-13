'use server';

import { TokensService } from '@/client/sdk.gen';

import type { ApiResult } from '@/types/api';

/**
 * Create a personal access token for Claude Code and return the setup prompt that
 * carries it. The prompt is copied, never shown.
 */
export const createSetupPromptAction = async (): Promise<string | null> => {
  const result = await TokensService.createPersonalAccessToken();
  return result.data?.setup_prompt ?? null;
};

/** Revoke one of the signed-in person's personal access tokens. */
export const revokePersonalAccessTokenAction = async (tokenId: string): Promise<ApiResult> => {
  const apiResponse = await TokensService.revokePersonalAccessToken({
    path: { token_id: tokenId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
