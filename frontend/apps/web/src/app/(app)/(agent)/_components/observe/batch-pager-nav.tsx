import { ChevronLeft, ChevronRight } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

interface BatchPagerNavProps {
  current: number;
  total: number;
  canPrev: boolean;
  canNext: boolean;
  onPrev?: () => void;
  onNext?: () => void;
  prevLabel?: string;
  nextLabel?: string;
}

export function BatchPagerNav({
  current,
  total,
  canPrev,
  canNext,
  onPrev,
  onNext,
  prevLabel = 'Previous',
  nextLabel = 'Next',
}: BatchPagerNavProps) {
  if (total <= 1) return null;

  return (
    <div className="flex items-center gap-0.5 rounded-md border border-border bg-accent/40 px-1 py-0.5">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onPrev}
        disabled={!canPrev}
        aria-label={prevLabel}
        className="h-5 w-5 rounded text-muted-foreground hover:bg-transparent hover:text-foreground disabled:opacity-30 [&_svg]:size-3.5"
      >
        <ChevronLeft />
      </Button>

      <span className="min-w-8.5 px-1 text-center text-[11px] tabular-nums text-foreground">
        {current} / {total}
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onNext}
        disabled={!canNext}
        aria-label={nextLabel}
        className="h-5 w-5 rounded text-muted-foreground hover:bg-transparent hover:text-foreground disabled:opacity-30 [&_svg]:size-3.5"
      >
        <ChevronRight />
      </Button>
    </div>
  );
}
