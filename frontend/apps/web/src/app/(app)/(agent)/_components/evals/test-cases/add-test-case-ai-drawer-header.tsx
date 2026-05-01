'use client';

import { ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { SheetDescription, SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';

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

        {carousel && carousel.total > 1 && (
          <div className="flex shrink-0 items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={carousel.onPrev}
              disabled={!carousel.canScrollPrev}
              aria-label="Previous test case"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            <span className="min-w-10 text-center text-[11px] tabular-nums text-muted-foreground">
              {carousel.current + 1} of {carousel.total}
            </span>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={carousel.onNext}
              disabled={!carousel.canScrollNext}
              aria-label="Next test case"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </SheetHeader>
  );
}
