'use client';

import { Sparkles } from 'lucide-react';

import { SheetDescription, SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';

import { BatchPagerNav } from '@/app/(app)/(agent)/_components/observe/batch-pager-nav';

interface CarouselNav {
  current: number;
  total: number;
  canScrollPrev: boolean;
  canScrollNext: boolean;
  onPrev: () => void;
  onNext: () => void;
}

interface AddTestCaseAiDrawerHeaderProps {
  variant?: 'input' | 'results';
  carousel?: CarouselNav;
}

export function AddTestCaseAiDrawerHeader({
  variant = 'input',
  carousel,
}: AddTestCaseAiDrawerHeaderProps) {
  const isResults = variant === 'results';

  return (
    <SheetHeader className="shrink-0 space-y-0 border-b border-border px-5 pb-4 pt-5 text-left">
      <div className="flex items-center justify-between gap-2.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/15">
            <Sparkles className="h-4 w-4 text-violet-400" />
          </div>
          <div>
            <SheetTitle className="text-sm font-normal text-foreground">
              {isResults ? 'Generated test cases' : 'Generate with AI'}
            </SheetTitle>

            <SheetDescription className="mt-0.5 text-[11px] text-muted-foreground">
              {isResults ? 'Review what AI created' : 'Describe the scenario to cover'}
            </SheetDescription>
          </div>
        </div>

        {carousel ? (
          <div className="shrink-0 pr-4">
            <BatchPagerNav
              current={carousel.current + 1}
              total={carousel.total}
              canPrev={carousel.canScrollPrev}
              canNext={carousel.canScrollNext}
              onPrev={carousel.onPrev}
              onNext={carousel.onNext}
              prevLabel="Previous test case"
              nextLabel="Next test case"
            />
          </div>
        ) : null}
      </div>
    </SheetHeader>
  );
}
