'use client';

import { useState } from 'react';

import { useDeleteTestCases } from '@/app/(app)/(agent)/_hooks/use-delete-test-cases';

import type { TestCasePublic } from '@/client/types.gen';

interface UseTestCasesDeletionParams {
  agentId: string;
  onDeleted?: (ids: string[]) => void;
}

export function useTestCasesDeletion({ agentId, onDeleted }: UseTestCasesDeletionParams) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [targets, setTargets] = useState<TestCasePublic[]>([]);
  const { mutateAsync, isPending } = useDeleteTestCases(agentId);

  const requestBatch = (items: TestCasePublic[]) => {
    setTargets(items);
    setDialogOpen(true);
  };

  const requestSingle = (testCase: TestCasePublic) => {
    setTargets([testCase]);
    setDialogOpen(true);
  };

  const confirm = async () => {
    try {
      const targetIds = targets.map((item) => item.id);
      await mutateAsync(targetIds);
      onDeleted?.(targetIds);
      setDialogOpen(false);
      setTargets([]);
    } catch {
      // stay open so the user can retry
    }
  };

  const onOpenChange = (open: boolean) => {
    setDialogOpen(open);
    if (!open) setTargets([]);
  };

  return {
    dialogOpen,
    targets,
    isPending,
    requestBatch,
    requestSingle,
    confirm,
    onOpenChange,
  };
}
