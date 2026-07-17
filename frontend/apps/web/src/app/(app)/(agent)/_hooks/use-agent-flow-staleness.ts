'use client';

import { useQuery } from '@tanstack/react-query';

import { agentFlowStalenessQuery } from '@/app/(app)/(agent)/_queries/agent-flow-staleness-query';
import { isConversationFlowAgent } from '@/app/(app)/(agent)/_constants/agent';

import type { AgentPublic } from '@/client/types.gen';

/**
 * Checks Retell for a newer conversation-flow version, once per browser
 * session per agent. No-op (disabled) for non-flow agents — most agents never
 * fire this request at all.
 */
export function useAgentFlowStaleness(
  agentId: string,
  agent: Pick<AgentPublic, 'agent_model'> | null | undefined
) {
  return useQuery({
    ...agentFlowStalenessQuery(agentId),
    enabled: isConversationFlowAgent(agent),
  });
}
