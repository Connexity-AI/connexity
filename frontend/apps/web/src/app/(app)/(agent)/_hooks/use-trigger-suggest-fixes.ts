'use client';

import { useCallback } from 'react';

import { useRouter } from 'next/navigation';

import {
  useSuggestFixes,
  type SuggestFixesCaseSummary,
} from '@/app/(app)/(agent)/_context/suggest-fixes-context';
import { UrlGenerator } from '@/common/url-generator/url-generator';

import type { TestCasePublic, TestCaseResultPublic } from '@/client/types.gen';

interface UseTriggerSuggestFixesArgs {
  agentId: string;
  runId: string;
  results: TestCaseResultPublic[];
  selectedIds: Set<string>;
  testCaseById: Map<string, TestCasePublic>;
}

export function useTriggerSuggestFixes({
  agentId,
  runId,
  results,
  selectedIds,
  testCaseById,
}: UseTriggerSuggestFixesArgs) {
  const router = useRouter();
  const { setAttachment } = useSuggestFixes();

  return useCallback(() => {
    const summaries: SuggestFixesCaseSummary[] = [];
    for (const result of results) {
      if (!selectedIds.has(result.id)) continue;
      const testCase = testCaseById.get(result.test_case_id);
      summaries.push({
        testCaseResultId: result.id,
        testCaseId: result.test_case_id,
        testCaseName: testCase?.name ?? 'Unknown test case',
        passed: result.passed ?? null,
        overallScore: result.verdict?.overall_score ?? null,
      });
    }
    if (summaries.length === 0) return;

    setAttachment({
      runId,
      testCaseResultIds: summaries.map((s) => s.testCaseResultId),
      caseSummaries: summaries,
    });

    router.push(UrlGenerator.agentEdit(agentId));
  }, [agentId, runId, results, selectedIds, testCaseById, setAttachment, router]);
}
