'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

import { testCaseResultsByRunQuery } from '@/app/(app)/(agent)/_queries/test-case-results-by-run-query';

export function useTestCaseResultsByRun(runId: string) {
  return useSuspenseQuery(testCaseResultsByRunQuery(runId));
}
