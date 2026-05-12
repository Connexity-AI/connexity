'use client';

import { useQuery } from '@tanstack/react-query';

import { agentVersionsListQuery } from '@/app/(app)/(agent)/_queries/agent-versions-list-query';

export function useAgentVersions(agentId: string, enabled: boolean = true) {
  return useQuery({
    ...agentVersionsListQuery(agentId),
    enabled,
  });
}
