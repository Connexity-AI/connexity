'use client';
'use no memo';

import { SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';

interface TestCaseDrawerHeaderProps {
  testCaseName: string | undefined;
}

export function TestCaseDrawerHeader({ testCaseName }: TestCaseDrawerHeaderProps) {
  return (
    <SheetHeader className="flex h-13 shrink-0 flex-row items-center justify-between space-y-0 border-b border-border pl-4 pr-10 text-left">
      <div className="flex min-w-0 items-center gap-2">
        <SheetTitle className="max-w-[220px] truncate text-sm font-normal text-foreground">
          {testCaseName ?? 'Test case'}
        </SheetTitle>
      </div>
    </SheetHeader>
  );
}
