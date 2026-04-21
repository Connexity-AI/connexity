'use client';
'use no memo';

import { useFormContext } from 'react-hook-form';

import { SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';

import { StatusBadge } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';

import type { TestCaseFormValues } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';

export function TestCaseDrawerHeader({ testCaseName }: { testCaseName: string | undefined }) {
  const form = useFormContext<TestCaseFormValues>();
  const status = form.watch('status');

  return (
    <SheetHeader className="flex h-13 shrink-0 flex-row items-center justify-between space-y-0 border-b border-border px-4 text-left">
      <div className="flex min-w-0 items-center gap-2">
        <SheetTitle className="truncate text-sm font-normal text-foreground">
          {testCaseName ?? 'Test case'}
        </SheetTitle>

        <StatusBadge status={status} />
      </div>
    </SheetHeader>
  );
}
