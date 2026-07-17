'use client';

import { useQuery } from '@tanstack/react-query';

import { agentRequirementsQuery } from '@/app/(app)/(agent)/_queries/agent-requirements-query';

export function useAgentRequirements(agentId: string, enabled: boolean = true) {
  return useQuery({
    ...agentRequirementsQuery(agentId),
    enabled,
    // While extraction is running (initial import or a re-extract), poll so the
    // UI flips to the result without a manual refresh.
    refetchInterval: (query) =>
      query.state.data?.status === 'extracting' ? 2500 : false,
  });
}
