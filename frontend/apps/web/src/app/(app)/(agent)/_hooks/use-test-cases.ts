'use client';

import { useQuery, useSuspenseQuery } from '@tanstack/react-query';

import { testCasesListQuery } from '@/app/(app)/(agent)/_queries/test-cases-list-query';

export function useTestCases(agentId: string) {
  return useQuery(testCasesListQuery(agentId));
}

export function useSuspenseTestCases(agentId: string) {
  return useSuspenseQuery(testCasesListQuery(agentId));
}
