import { cn } from '@workspace/ui/lib/utils';

import { roundScore, scoreColor } from './shared/score-utils';

import type { AggregateMetrics, RunStatus } from '@/client/types.gen';

interface EvalRunMetricsBarProps {
  metrics: AggregateMetrics | null | undefined;
  status: RunStatus;
}

export function EvalRunMetricsBar({ metrics, status }: EvalRunMetricsBarProps) {
  if (status !== 'completed') return null;
  if (!metrics) return null;

  const avgScore = roundScore(metrics.avg_overall_score);
  const { text: scoreText } = scoreColor(avgScore);
  const scoreLabel = avgScore === null ? '—' : `${avgScore}/100`;

  return (
    <div className="flex shrink-0 items-center gap-4 border-b border-border px-6 py-3 text-xs">
      <span className={cn('font-mono tabular-nums', scoreText)}>{scoreLabel}</span>
      <span className="text-muted-foreground">|</span>
      <span className="text-green-400">{metrics.passed_count} passed</span>
      <span className="text-red-400">{metrics.failed_count} failed</span>
      <ErroredCount count={metrics.error_count} />
      <span className="ml-auto text-muted-foreground">
        {metrics.total_executions} total
      </span>
    </div>
  );
}

function ErroredCount({ count }: { count: number }) {
  if (count <= 0) return null;
  return <span className="text-yellow-400">{count} errored</span>;
}
