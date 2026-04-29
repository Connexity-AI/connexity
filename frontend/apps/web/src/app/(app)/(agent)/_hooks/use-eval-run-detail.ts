'use client';

import { useMemo, useState } from 'react';

import { useEvalRun } from '@/app/(app)/(agent)/_hooks/use-eval-run';
import { useTestCaseResultsByRun } from '@/app/(app)/(agent)/_hooks/use-test-case-results-by-run';

import type { EvalConfigPublic, TestCasePublic } from '@/client/types.gen';

export type ResultFilter = 'all' | 'passed' | 'failed';

interface UseEvalRunDetailParams {
  runId: string;
  configs: EvalConfigPublic[];
  testCases: TestCasePublic[];
}

export function useEvalRunDetail({ runId, configs, testCases }: UseEvalRunDetailParams) {
  const { data: run } = useEvalRun(runId);
  const { data: resultsData } = useTestCaseResultsByRun(runId);

  const [filter, setFilter] = useState<ResultFilter>('all');
  const [drawerResultId, setDrawerResultId] = useState<string | null>(null);

  const results = useMemo(() => resultsData?.data ?? [], [resultsData]);

  const configName = useMemo(() => {
    const config = configs.find((c) => c.id === run.eval_config_id);
    return config?.name ?? 'Unknown config';
  }, [configs, run.eval_config_id]);

  const testCaseById = useMemo(() => {
    const map = new Map<string, TestCasePublic>();
    for (const tc of testCases) map.set(tc.id, tc);
    return map;
  }, [testCases]);

  const { passedCount, failedCount } = useMemo(() => {
    let passed = 0;
    let failed = 0;
    for (const r of results) {
      if (r.passed === true) passed += 1;
      else if (r.passed === false) failed += 1;
    }
    return { passedCount: passed, failedCount: failed };
  }, [results]);

  const filteredResults = useMemo(() => {
    if (filter === 'all') return results;
    if (filter === 'passed') return results.filter((r) => r.passed === true);
    return results.filter((r) => r.passed === false);
  }, [results, filter]);

  const drawerResult =
    drawerResultId !== null ? results.find((r) => r.id === drawerResultId) ?? null : null;

  return {
    run,
    results,
    filteredResults,
    configName,
    testCaseById,
    passedCount,
    failedCount,
    filter,
    setFilter,
    drawerResultId,
    setDrawerResultId,
    drawerResult,
  };
}
