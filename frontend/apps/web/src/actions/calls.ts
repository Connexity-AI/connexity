'use server';

import { CallsService } from '@/client/sdk.gen';
import { isSuccessApiResult } from '@/utils/api';

import type {
  CallLabel,
  CallPublic,
  CallRefreshResult,
  CallsPublic,
  CallTracePublic,
  ExecutionSyncResult,
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

export const setCallLabel = async (
  callId: string,
  label: CallLabel | null,
): Promise<ApiResult<CallPublic>> => {
  const apiResponse = await CallsService.setCallLabelEndpoint({
    path: { call_id: callId },
    body: { label },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

/** The call's trace, or `null` when the call has not been converted to one. */
export const getCallTrace = async (callId: string): Promise<CallTracePublic | null> => {
  const apiResponse = await CallsService.getCallTrace({
    path: { call_id: callId },
  });
  const { response: _, ...result } = apiResponse;
  return isSuccessApiResult<CallTracePublic>(result) ? result.data : null;
};

/** Look again in the mapped backends for what happened behind a call's tool calls. */
export const refreshCallExecutions = async (
  callId: string,
): Promise<ApiResult<ExecutionSyncResult>> => {
  const apiResponse = await CallsService.refreshCallExecutions({
    path: { call_id: callId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
