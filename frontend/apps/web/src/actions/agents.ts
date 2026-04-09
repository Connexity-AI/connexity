'use server';

import { AgentsService } from '@/client/sdk.gen';
import { isSuccessApiResult } from '@/utils/api';

import type {
  AgentCreate,
  AgentDraftUpdate,
  AgentPublic,
  AgentRollbackRequest,
  AgentUpdate,
  AgentVersionPublic,
  AgentVersionsPublic,
  PublishRequest,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export type AgentRow = AgentPublic;

export type AgentFilters = {
  name?: string;
  page?: number;
  pageSize?: number;
};

export type GetAgentsResult = {
  rows: AgentRow[];
  totalCount: number;
};

export const getAgents = async (filters: AgentFilters = {}): Promise<GetAgentsResult> => {
  const page = filters.page ?? 1;
  const pageSize = filters.pageSize ?? 10;
  const skip = (page - 1) * pageSize;

  const apiResponse = await AgentsService.listAgents({
    query: { skip, limit: pageSize },
  });

  const { response: _, ...result } = apiResponse;

  if (!isSuccessApiResult(result)) {
    return { rows: [], totalCount: 0 };
  }

  return {
    rows: result.data.data,
    totalCount: result.data.count,
  };
};

export const deleteAgent = async (agentId: string): Promise<{ success: boolean }> => {
  const apiResponse = await AgentsService.deleteAgent({
    path: { agent_id: agentId },
  });

  const { response: _, ...result } = apiResponse;

  return { success: isSuccessApiResult(result) };
};

export const createAgent = async (body: AgentCreate): Promise<ApiResult<AgentPublic>> => {
  const apiResponse = await AgentsService.createAgent({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const createDraftAgent = async (
  name: string = 'Untitled Agent'
): Promise<ApiResult<AgentPublic>> => {
  const { client } = await import('@/client/client.gen');
  const apiResponse = await client.post({
    url: '/api/v1/agents/draft',
    body: { name },
    headers: { 'Content-Type': 'application/json' },
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<AgentPublic>;
};

export const getAgent = async (agentId: string): Promise<ApiResult<AgentPublic>> => {
  const apiResponse = await AgentsService.getAgent({
    path: { agent_id: agentId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const updateAgent = async (
  agentId: string,
  body: AgentUpdate
): Promise<ApiResult<AgentPublic>> => {
  const apiResponse = await AgentsService.updateAgent({
    path: { agent_id: agentId },
    body,
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const getAgentVersions = async (
  agentId: string,
  skip: number = 0,
  limit: number = 100
): Promise<ApiResult<AgentVersionsPublic>> => {
  const apiResponse = await AgentsService.listAgentVersions({
    path: { agent_id: agentId },
    query: { skip, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<AgentVersionsPublic>;
};

export const getAgentVersion = async (
  agentId: string,
  version: number
): Promise<ApiResult<AgentVersionPublic>> => {
  const apiResponse = await AgentsService.readAgentVersion({
    path: { agent_id: agentId, version },
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<AgentVersionPublic>;
};

export const getAgentDraft = async (
  agentId: string
): Promise<ApiResult<AgentVersionPublic>> => {
  const apiResponse = await AgentsService.getDraft({
    path: { agent_id: agentId },
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<AgentVersionPublic>;
};

export const upsertAgentDraft = async (
  agentId: string,
  body: AgentDraftUpdate
): Promise<ApiResult<AgentVersionPublic>> => {
  const apiResponse = await AgentsService.upsertDraft({
    path: { agent_id: agentId },
    body,
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<AgentVersionPublic>;
};

export const publishAgentDraft = async (
  agentId: string,
  body: PublishRequest
): Promise<ApiResult<AgentVersionPublic>> => {
  const apiResponse = await AgentsService.publishDraft({
    path: { agent_id: agentId },
    body,
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<AgentVersionPublic>;
};

export const rollbackAgentVersion = async (
  agentId: string,
  body: AgentRollbackRequest
): Promise<ApiResult<AgentVersionPublic>> => {
  const apiResponse = await AgentsService.rollbackAgent({
    path: { agent_id: agentId },
    body,
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<AgentVersionPublic>;
};
