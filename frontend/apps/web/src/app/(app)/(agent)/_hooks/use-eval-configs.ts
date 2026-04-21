'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { evalConfigsListQuery } from '@/app/(app)/(agent)/_queries/eval-configs-list-query';

export function useEvalConfigs(agentId: string) {
  return useSuspenseQuery(evalConfigsListQuery(agentId));
}
