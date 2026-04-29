import { format } from 'date-fns';
import { CheckCircle2, XCircle } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { roundScore, scoreColor } from './shared/score-utils';

import type { RunPublic, RunStatus } from '@/client/types.gen';

interface EvalRunMetricsBarProps {
  run: RunPublic;
  status: RunStatus;
}

export function EvalRunMetricsBar({ run, status }: EvalRunMetricsBarProps) {
  if (status !== 'completed') return null;
  const metrics = run.aggregate_metrics;
  if (!metrics) return null;

  const avgScore = roundScore(metrics.avg_overall_score);
  const { text: scoreText, bar: scoreBar } = scoreColor(avgScore);
  const scorePct = Math.max(0, Math.min(100, avgScore ?? 0));
  const scoreDisplay = avgScore === null ? '—' : avgScore;

  const dateIso = run.completed_at ?? run.started_at ?? run.created_at;
  const dateObj = dateIso ? new Date(dateIso) : null;
  const longDate = dateObj ? format(dateObj, 'MMM d, yyyy') : '—';
  const shortDate = dateObj ? format(dateObj, 'M/d/yyyy') : '—';

  return (
    <div className="flex shrink-0 items-center gap-4 border-b border-border px-6 py-3 text-xs">
      <div className="flex items-center gap-3">
        <div className="flex items-baseline gap-0.5 font-mono tabular-nums">
          <span className={cn('text-lg font-semibold leading-none', scoreText)}>
            {scoreDisplay}
          </span>
          <span className="text-xs text-muted-foreground">/100</span>
        </div>
        <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
          <div
            className={cn('h-full rounded-full', scoreBar)}
            style={{ width: `${scorePct}%` }}
          />
        </div>
      </div>

      <span className="text-border">|</span>

      <span className="text-muted-foreground">
        {metrics.unique_test_case_count} conversations
      </span>
      <span className="flex items-center gap-1 text-green-400">
        <CheckCircle2 className="h-3.5 w-3.5" />
        {metrics.passed_count} passed
      </span>
      <span className="flex items-center gap-1 text-red-400">
        <XCircle className="h-3.5 w-3.5" />
        {metrics.failed_count} failed
      </span>
      <ErroredCount count={metrics.error_count} />

      <span className="ml-auto text-border">|</span>
      <span className="text-muted-foreground">
        {longDate} · {shortDate}
      </span>
      <span className="text-muted-foreground">Manual</span>
    </div>
  );
}

function ErroredCount({ count }: { count: number }) {
  if (count <= 0) return null;
  return <span className="text-yellow-400">{count} errored</span>;
}
