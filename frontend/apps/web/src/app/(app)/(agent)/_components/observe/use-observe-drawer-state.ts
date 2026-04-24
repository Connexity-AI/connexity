'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { useTestCasesDeletion } from '@/app/(app)/(agent)/_components/evals/test-cases/use-test-cases-deletion';
import { useMarkCallSeen } from '@/app/(app)/(agent)/_hooks/use-calls';
import { useTestCases } from '@/app/(app)/(agent)/_hooks/use-test-cases';

import type { ObserveRightPanelMode } from './observe-drawer';
import type { CallPublic, TestCasePublic } from '@/client/types.gen';

interface UseObserveDrawerStateParams {
  agentId: string;
  calls: CallPublic[];
}

interface UseObserveDrawerStateResult {
  selectedCall: CallPublic | null;
  selectedTestCase: TestCasePublic | null;
  rightPanelMode: ObserveRightPanelMode | null;
  testCasesByCallId: Map<string, TestCasePublic[]>;
  onRowClick: (call: CallPublic) => void;
  onTestCaseClick: (call: CallPublic, testCase: TestCasePublic) => void;
  onCloseDrawer: () => void;
  onCloseRightPanel: () => void;
  onCreateTestCaseManual: () => void;
  onCreateTestCaseAi: () => void;
  onAiGenerated: (testCaseId: string) => void;
  deletion: ReturnType<typeof useTestCasesDeletion>;
}

export function useObserveDrawerState({
  agentId,
  calls,
}: UseObserveDrawerStateParams): UseObserveDrawerStateResult {
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [rightPanelMode, setRightPanelMode] = useState<ObserveRightPanelMode | null>(null);
  const [selectedTestCaseId, setSelectedTestCaseId] = useState<string | null>(null);
  const [pendingTestCaseId, setPendingTestCaseId] = useState<string | null>(null);

  const markSeen = useMarkCallSeen(agentId);

  const testCasesQuery = useTestCases(agentId);
  const testCases = useMemo(() => testCasesQuery.data?.data ?? [], [testCasesQuery.data]);

  const deletion = useTestCasesDeletion({
    agentId,
    onDeleted: (ids) => {
      if (selectedTestCaseId && ids.includes(selectedTestCaseId)) {
        setSelectedTestCaseId(null);
        setRightPanelMode(null);
      }
    },
  });

  const selectedCall = useMemo<CallPublic | null>(
    () => calls.find((c) => c.id === selectedCallId) ?? null,
    [calls, selectedCallId],
  );

  const selectedTestCase = useMemo<TestCasePublic | null>(
    () => testCases.find((tc) => tc.id === selectedTestCaseId) ?? null,
    [testCases, selectedTestCaseId],
  );

  const testCasesByCallId = useMemo(() => {
    const map = new Map<string, TestCasePublic[]>();
    for (const tc of testCases) {
      if (!tc.source_call_id) continue;
      const existing = map.get(tc.source_call_id);
      if (existing) {
        existing.push(tc);
      } else {
        map.set(tc.source_call_id, [tc]);
      }
    }
    return map;
  }, [testCases]);

  // After AI generation, wait for the newly created test case to land in the
  // list cache, then switch the right panel over to it.
  useEffect(() => {
    if (!pendingTestCaseId) return;
    const found = testCases.find((tc) => tc.id === pendingTestCaseId);
    if (!found) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing UI mode with async list refetch after AI generation
    setSelectedTestCaseId(found.id);
    setRightPanelMode('test-case');
    setPendingTestCaseId(null);
  }, [pendingTestCaseId, testCases]);

  const onRowClick = useCallback(
    (call: CallPublic) => {
      setSelectedCallId(call.id);
      if (call.is_new) markSeen.mutate(call.id);
    },
    [markSeen],
  );

  const onTestCaseClick = useCallback(
    (call: CallPublic, testCase: TestCasePublic) => {
      setSelectedCallId(call.id);
      setSelectedTestCaseId(testCase.id);
      setRightPanelMode('test-case');
      setPendingTestCaseId(null);
      if (call.is_new) markSeen.mutate(call.id);
    },
    [markSeen],
  );

  const onCloseDrawer = useCallback(() => {
    setSelectedCallId(null);
    setSelectedTestCaseId(null);
    setRightPanelMode(null);
    setPendingTestCaseId(null);
  }, []);

  const onCloseRightPanel = useCallback(() => {
    setRightPanelMode(null);
    setSelectedTestCaseId(null);
    setPendingTestCaseId(null);
  }, []);

  const onCreateTestCaseManual = useCallback(() => {
    setRightPanelMode('manual-create');
    setSelectedTestCaseId(null);
    setPendingTestCaseId(null);
  }, []);

  const onCreateTestCaseAi = useCallback(() => {
    setRightPanelMode('ai-prompt');
    setSelectedTestCaseId(null);
  }, []);

  const onAiGenerated = useCallback(
    (testCaseId: string) => {
      const found = testCases.find((tc) => tc.id === testCaseId);
      if (found) {
        setSelectedTestCaseId(testCaseId);
        setRightPanelMode('test-case');
        setPendingTestCaseId(null);
      } else {
        setPendingTestCaseId(testCaseId);
      }
    },
    [testCases],
  );

  return {
    selectedCall,
    selectedTestCase,
    rightPanelMode,
    testCasesByCallId,
    onRowClick,
    onTestCaseClick,
    onCloseDrawer,
    onCloseRightPanel,
    onCreateTestCaseManual,
    onCreateTestCaseAi,
    onAiGenerated,
    deletion,
  };
}
