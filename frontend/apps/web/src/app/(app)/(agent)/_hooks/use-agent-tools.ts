'use client';

import { useMemo } from 'react';

import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { mapAgentToForm } from '@/app/(app)/(agent)/_utils/map-agent-to-form';

import type { AgentToolValues } from '@/app/(app)/(agent)/_schemas/agent-form';

/** Tools of the agent's current version, in the shape test case forms expect. */
export function useAgentTools(agentId: string): AgentToolValues[] {
  const { data: agent } = useAgent(agentId);

  return useMemo(() => (agent ? mapAgentToForm(agent).tools : []), [agent]);
}
