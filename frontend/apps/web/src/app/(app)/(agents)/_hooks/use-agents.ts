'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { AgentService } from '@/app/(app)/(agents)/_service';
import { type AgentFilters } from '@/actions/agents';

export const useAgents = (filters: AgentFilters) => {
  return useQuery({
    ...AgentService.getAgentsQuery(filters),
    placeholderData: keepPreviousData,
  });
};
