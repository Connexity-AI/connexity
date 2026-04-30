'use client';
'use no memo';

import { Sparkles } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';

import { StatusBadge } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';

import type { TestCaseFormValues } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';

interface TestCaseDrawerHeaderProps {
  testCaseName: string | undefined;
  onOpenAiEdit?: () => void;
}

export function TestCaseDrawerHeader({ testCaseName, onOpenAiEdit }: TestCaseDrawerHeaderProps) {
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

      {onOpenAiEdit && (
        <button
          type="button"
          onClick={onOpenAiEdit}
          title="AI Assistant"
          className="flex h-7 shrink-0 cursor-pointer items-center gap-1.5 rounded-md border border-violet-500/25 bg-violet-500/10 px-2 text-[11px] text-violet-300 transition-colors hover:bg-violet-500/20"
        >
          <Sparkles className="h-3 w-3" />
          AI Assistant
        </button>
      )}
    </SheetHeader>
  );
}
