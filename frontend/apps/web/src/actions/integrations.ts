'use server';

import { IntegrationsService, ToolBackendsService } from '@/client/sdk.gen';

import type {
  AgentToolPublic,
  IntegrationCreate,
  IntegrationPublic,
  IntegrationsPublic,
  Message,
  RetellAgentSummary,
  ToolBackendPublic,
  ToolBackendSet,
  WorkflowSummary,
} from '@/client/types.gen';
import type { ApiResult } from '@/types/api';

export const createIntegration = async (
  body: IntegrationCreate
): Promise<ApiResult<IntegrationPublic>> => {
  const apiResponse = await IntegrationsService.createIntegration({ body });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listIntegrations = async (
  skip = 0,
  limit = 100
): Promise<ApiResult<IntegrationsPublic>> => {
  const apiResponse = await IntegrationsService.listIntegrations({
    query: { skip, limit },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const deleteIntegration = async (id: string): Promise<ApiResult<void>> => {
  const apiResponse = await IntegrationsService.deleteIntegration({
    path: { integration_id: id },
  });
  const { response: _, ...result } = apiResponse;
  return result as ApiResult<void>;
};

export const testIntegration = async (id: string): Promise<ApiResult<{ message: string }>> => {
  const apiResponse = await IntegrationsService.testIntegration({
    path: { integration_id: id },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listRetellAgents = async (
  integrationId: string
): Promise<ApiResult<RetellAgentSummary[]>> => {
  const apiResponse = await IntegrationsService.listIntegrationAgents({
    path: { integration_id: integrationId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listVapiAssistants = async (
  integrationId: string
): Promise<ApiResult<RetellAgentSummary[]>> => {
  const apiResponse = await IntegrationsService.listIntegrationAgents({
    path: { integration_id: integrationId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const listElevenlabsAgents = async (
  integrationId: string
): Promise<ApiResult<RetellAgentSummary[]>> => {
  const apiResponse = await IntegrationsService.listIntegrationAgents({
    path: { integration_id: integrationId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

/** The tools seen in an agent's calls, each with the workflow it is mapped to. */
export const listAgentTools = async (agentId: string): Promise<ApiResult<AgentToolPublic[]>> => {
  const apiResponse = await ToolBackendsService.toolBackendsListAgentTools({
    path: { agent_id: agentId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const setToolBackend = async (
  agentId: string,
  body: ToolBackendSet
): Promise<ApiResult<ToolBackendPublic>> => {
  const apiResponse = await ToolBackendsService.toolBackendsSetAgentToolBackend({
    path: { agent_id: agentId },
    body,
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

export const clearToolBackend = async (
  agentId: string,
  toolName: string
): Promise<ApiResult<Message>> => {
  const apiResponse = await ToolBackendsService.toolBackendsClearAgentToolBackend({
    path: { agent_id: agentId },
    query: { tool_name: toolName },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};

/** The workflows of an n8n connection, for choosing one. */
export const listIntegrationWorkflows = async (
  integrationId: string
): Promise<ApiResult<WorkflowSummary[]>> => {
  const apiResponse = await IntegrationsService.listIntegrationWorkflows({
    path: { integration_id: integrationId },
  });
  const { response: _, ...result } = apiResponse;
  return result;
};
