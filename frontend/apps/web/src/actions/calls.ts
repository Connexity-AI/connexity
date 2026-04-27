'use server';

import { CallsService } from '@/client/sdk.gen';
import { isSuccessApiResult } from '@/utils/api';

import type {
  CallPublic,
  CallRefreshResult,
  CallsPublic,
  Message,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export type CallRow = CallPublic;

export type GetCallsResult = {
  rows: CallRow[];
  totalCount: number;
};

export type CallQueryFilters = {
  page?: number;
  pageSize?: number;
  dateFrom?: string | null;
  dateTo?: string | null;
};

export const getCalls = async (
  agentId: string,
  filters: CallQueryFilters = {},
): Promise<GetCallsResult> => {
  const page = filters.page ?? 1;
  const pageSize = filters.pageSize ?? 25;
  const skip = (page - 1) * pageSize;

  const apiResponse = await CallsService.listAgentCalls({
    path: { agent_id: agentId },
    query: {
      skip,
      limit: pageSize,
      date_from: filters.dateFrom ?? undefined,
      date_to: filters.dateTo ?? undefined,
    },
  });

  const { response: _, ...result } = apiResponse;

  if (!isSuccessApiResult<CallsPublic>(result)) {
    return { rows: [], totalCount: 0 };
  }
  return { rows: result.data.data, totalCount: result.data.count };
};

export const refreshCalls = async (
  agentId: string,
): Promise<ApiResult<CallRefreshResult>> => {
  const apiResponse = await CallsService.refreshAgentCalls({
    path: { agent_id: agentId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const markCallSeen = async (
  callId: string,
): Promise<ApiResult<Message>> => {
  const apiResponse = await CallsService.markCallSeenEndpoint({
    path: { call_id: callId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
