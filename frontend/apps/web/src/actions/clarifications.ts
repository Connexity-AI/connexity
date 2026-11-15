'use server';

import { revalidatePath } from 'next/cache';

import { ClarificationsService } from '@/client/sdk.gen';

import type { ApiResult } from '@/types/api';

/**
 * Answer (a to d), park or reopen a clarification: the person's decision, recorded as
 * theirs. An answer becomes a spec rule and is final.
 */
export const decideClarificationAction = async (
  clarificationId: string,
  answer: string
): Promise<ApiResult> => {
  const apiResponse = await ClarificationsService.answerWorkspaceClarifications({
    body: { answers: [{ clarification_id: clarificationId, answer }] },
  });
  const { response: _, ...result } = apiResponse;
  revalidatePath('/', 'layout');
  return result;
};
