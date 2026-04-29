'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { evalRunsListQuery } from '@/app/(app)/(agent)/_queries/eval-runs-list-query';

export function useEvalRuns(agentId: string) {
  return useSuspenseQuery(evalRunsListQuery(agentId));
}
