import { cn } from '@workspace/ui/lib/utils';

import { SCORE_TYPE_META, TIER_META } from './metric-meta';

import type { MetricTier, ScoreType } from '@/client/types.gen';

export function TierBadge({ tier }: { tier: MetricTier }) {
  const m = TIER_META[tier];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] border',
        m.color
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', m.dot)} />
      {m.label}
    </span>
  );
}

export function ScoreTypeBadge({ type }: { type: ScoreType }) {
  const m = SCORE_TYPE_META[type];
  return <span className={cn('px-2 py-0.5 rounded text-[10px]', m.color)}>{m.label}</span>;
}
