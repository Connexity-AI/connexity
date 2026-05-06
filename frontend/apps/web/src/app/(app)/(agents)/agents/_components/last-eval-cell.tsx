'use client';

import { useMemo } from 'react';

import { useQuery } from '@tanstack/react-query';
import {
  CircleCheck,
  CircleX,
  Clock,
  FlaskConicalOff,
  ListChecks,
  Target,
} from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { evalRunsListQuery } from '@/app/(app)/(agent)/_queries/eval-runs-list-query';
import { roundScore } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/score-utils';
import { formatTimeAgo } from '@/app/(app)/(agent)/_utils/format-time-ago';
import { RunStatus } from '@/client/types.gen';

import type { RunPublic } from '@/client/types.gen';

interface LastEvalCellProps {
  agentId: string;
}

function pickLatestCompletedRun(runs: RunPublic[]): RunPublic | null {
  let latest: RunPublic | null = null;
  for (const run of runs) {
    if (run.status !== RunStatus.COMPLETED) continue;
    if (!latest || run.created_at > latest.created_at) {
      latest = run;
    }
  }
  return latest;
}

const PILL_BASE =
  'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-mono tabular-nums';
const PILL_PASS = 'bg-green-500/10 text-green-400 border-green-500/20';
const PILL_FAIL = 'bg-red-500/10 text-red-400 border-red-500/20';

export function LastEvalCell({ agentId }: LastEvalCellProps) {
  const { data, isLoading } = useQuery(evalRunsListQuery(agentId));
  const latest = useMemo(
    () => pickLatestCompletedRun(data?.data ?? []),
    [data]
  );

  if (isLoading) {
    return <span className="text-xs text-muted-foreground/40">…</span>;
  }

  if (!latest) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground/50">
        <FlaskConicalOff className="w-3.5 h-3.5" />
        <span className="text-xs">No eval run yet</span>
      </div>
    );
  }

  const metrics = latest.aggregate_metrics;
  const metricsScore = roundScore(metrics?.weighted_metrics_score_pct);
  const metricsPassed = metrics?.metrics_passed ?? null;
  const casesPassed = metrics?.cases_passed ?? null;
  const passedCount = metrics?.passed_count ?? 0;
  const totalExecutions = metrics?.total_executions ?? 0;
  const overallPassed = metricsPassed === true && casesPassed === true;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-[10px]">
        {metricsScore !== null && metricsPassed !== null ? (
          <span
            className={cn(PILL_BASE, metricsPassed ? PILL_PASS : PILL_FAIL)}
            title="Metrics score"
          >
            <Target className="w-2.5 h-2.5" />
            {metricsScore}%
          </span>
        ) : null}
        {casesPassed !== null ? (
          <span
            className={cn(PILL_BASE, casesPassed ? PILL_PASS : PILL_FAIL)}
            title="Cases passed"
          >
            <ListChecks className="w-2.5 h-2.5" />
            {passedCount}/{totalExecutions}
          </span>
        ) : null}
        {metricsPassed !== null && casesPassed !== null ? (
          overallPassed ? (
            <CircleCheck className="w-3.5 h-3.5 text-green-400 shrink-0" />
          ) : (
            <CircleX className="w-3.5 h-3.5 text-red-400 shrink-0" />
          )
        ) : null}
      </div>
      <p className="text-[10px] text-muted-foreground/50 flex items-center gap-1">
        <Clock className="w-2.5 h-2.5" />
        {formatTimeAgo(latest.created_at)}
      </p>
    </div>
  );
}
