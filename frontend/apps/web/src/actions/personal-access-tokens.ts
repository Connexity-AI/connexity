'use server';

import { TokensService } from '@/client/sdk.gen';

import type { ApiResult } from '@/types/api';

/** Revoke one of the signed-in person's personal access tokens. */
export const revokePersonalAccessTokenAction = async (tokenId: string): Promise<ApiResult> => {
  const apiResponse = await TokensService.revokePersonalAccessToken({
    path: { token_id: tokenId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
