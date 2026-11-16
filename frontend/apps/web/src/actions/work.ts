'use server';

import { revalidatePath } from 'next/cache';

import { WorkService } from '@/client/sdk.gen';

import type { WorkPublic } from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

/**
 * Move a To do task to sit just before another (none: the end). The person's order;
 * the assistant then gets tasks in it (plans/2026-11-16-reorder.md).
 */
export const moveWorkTaskAction = async (
  key: string,
  before: string | null
): Promise<ApiResult<WorkPublic>> => {
  const apiResponse = await WorkService.moveWorkTask({ body: { key, before } });
  const { response: _, ...result } = apiResponse;
  revalidatePath('/', 'layout');
  return result;
};
