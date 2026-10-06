import type { AgentPublic } from '@/client/types.gen';

/** The provider account and provider-side agent this agent is linked to. */
export type AgentProviderTarget = AgentPublic & {
  integration_id?: string | null;
  platform_agent_id?: string | null;
  platform_agent_name?: string | null;
};
