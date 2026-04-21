'use client';

import { useState } from 'react';

import type { TestCasePublic } from '@/client/types.gen';

export function useTestCaseDrawer() {
  const [open, setOpen] = useState(false);
  const [activeTestCase, setActiveTestCase] = useState<TestCasePublic | null>(null);

  const openFor = (testCase: TestCasePublic) => {
    setActiveTestCase(testCase);
    setOpen(true);
  };

  const close = () => {
    setOpen(false);
    setActiveTestCase(null);
  };

  const onOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) setActiveTestCase(null);
  };

  return {
    open,
    activeTestCase,
    openFor,
    close,
    onOpenChange,
  };
}
