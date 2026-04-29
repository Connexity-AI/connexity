import { cn } from '@workspace/ui/lib/utils';

import { scoreColor } from './score-utils';

interface ScoreBarProps {
  /** 0-100 */
  value: number | null | undefined;
  className?: string;
  /** Width of the outer track, e.g. "w-14" */
  trackClassName?: string;
}

export function ScoreBar({ value, className, trackClassName = 'w-14' }: ScoreBarProps) {
  const pct = Math.max(0, Math.min(100, value ?? 0));
  const { bar } = scoreColor(value);

  return (
    <div
      className={cn(
        'h-1 overflow-hidden rounded-full bg-accent/50',
        trackClassName,
        className
      )}
    >
      <div className={cn('h-full rounded-full', bar)} style={{ width: `${pct}%` }} />
    </div>
  );
}
