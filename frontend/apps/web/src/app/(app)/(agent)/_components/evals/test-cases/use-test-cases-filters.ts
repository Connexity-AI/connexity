'use client';

import { useMemo } from 'react';

import { useQueryStates } from 'nuqs';

import { testCasesParser } from '@/common/url-generator/parsers';

import type { TestCasePublic } from '@/client/types.gen';

export function useTestCasesFilters(testCases: TestCasePublic[]) {
  const [{ status: statusFilter, difficulty: difficultyFilter }, setFilters] =
    useQueryStates(testCasesParser);

  const filtered = useMemo(
    () =>
      testCases.filter((item) => {
        const status = item.status ?? 'active';
        const difficulty = item.difficulty ?? 'normal';
        if (statusFilter !== 'all' && status !== statusFilter) return false;
        if (difficultyFilter !== 'all' && difficulty !== difficultyFilter) return false;
        return true;
      }),
    [testCases, statusFilter, difficultyFilter]
  );

  const clearFilters = () => {
    setFilters({ status: 'active', difficulty: 'all' });
  };

  return {
    statusFilter,
    difficultyFilter,
    setFilters,
    filtered,
    clearFilters,
  };
}
