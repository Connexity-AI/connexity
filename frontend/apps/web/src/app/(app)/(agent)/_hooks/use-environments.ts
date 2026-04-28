'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { environmentsListQuery } from '@/app/(app)/(agent)/_queries/environments-list-query';

export function useEnvironments(agentId: string) {
  return useSuspenseQuery(environmentsListQuery(agentId));
}
