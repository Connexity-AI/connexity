'use server';

import { revalidatePath } from 'next/cache';

import { IssuesService } from '@/client/sdk.gen';

import type { ApiResult } from '@/types/api';

/** Archive an issue: a person's decision, with a reason and how long. */
export const archiveIssueAction = async (
  issueId: string,
  reason: string,
  duration: 'until_spike' | 'forever'
): Promise<ApiResult> => {
  const apiResponse = await IssuesService.setIssueState({
    path: { issue_id: issueId },
    body: { state: 'archived', reason, duration },
  });
  const { response: _, ...result } = apiResponse;
  revalidatePath(`/issues/${issueId}`);
  return result;
};
