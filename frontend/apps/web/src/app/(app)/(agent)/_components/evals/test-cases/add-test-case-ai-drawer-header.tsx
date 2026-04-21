'use client';

import { Sparkles } from 'lucide-react';

import { SheetDescription, SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';

export function AddTestCaseAiDrawerHeader() {
  return (
    <SheetHeader className="shrink-0 space-y-0 border-b border-border px-5 pb-4 pt-5 text-left">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/15">
          <Sparkles className="h-4 w-4 text-violet-400" />
        </div>
        <div>
          <SheetTitle className="text-sm font-normal text-foreground">Generate with AI</SheetTitle>

          <SheetDescription className="mt-0.5 text-[11px] text-muted-foreground">
            Describe the scenario to cover
          </SheetDescription>
        </div>
      </div>
    </SheetHeader>
  );
}
