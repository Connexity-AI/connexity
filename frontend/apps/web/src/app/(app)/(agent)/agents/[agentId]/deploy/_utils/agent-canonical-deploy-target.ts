import type { AgentPublic } from '@/client/types.gen';

/** canonical deploy target fields on Agent (OpenAPI may lag until client regen) */
export type AgentCanonicalDeployTarget = AgentPublic & {
  integration_id?: string | null;
  platform_agent_id?: string | null;
  platform_agent_name?: string | null;
};
