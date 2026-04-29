'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { evalRunDetailQuery } from '@/app/(app)/(agent)/_queries/eval-run-detail-query';

export function useEvalRun(runId: string) {
  return useSuspenseQuery(evalRunDetailQuery(runId));
}
