'use client';

import { CircleCheck, CircleX, ListChecks, Target } from 'lucide-react';
import Link from 'next/link';

import { cn } from '@workspace/ui/lib/utils';

import { roundScore } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/score-utils';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { RunStatus } from '@/client/types.gen';

import type { RunPublic } from '@/client/types.gen';
import type { FC } from 'react';

const PILL =
  'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-mono tabular-nums';
const PILL_PASS = 'bg-green-500/10 text-green-400 border-green-500/20';
const PILL_FAIL = 'bg-red-500/10 text-red-400 border-red-500/20';

interface Props {
  run: RunPublic | undefined;
  agentId: string;
}

export const GatePills: FC<Props> = ({ run, agentId }) => {
  if (!run) {
    return <span className="text-[10px] text-muted-foreground/50">No run yet</span>;
  }
  if (run.status === RunStatus.PENDING || run.status === RunStatus.RUNNING) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="w-3 h-3 rounded-full border-2 border-violet-400/40 border-t-violet-400 animate-spin shrink-0" />
        <span className="text-[10px] text-violet-400">Running…</span>
      </div>
    );
  }

  const m = run.aggregate_metrics;
  const score = roundScore(m?.weighted_metrics_score_pct);
  const metricsPassed = m?.metrics_passed ?? null;
  const casesPassed = m?.cases_passed ?? null;
  const passedCount = m?.passed_count ?? 0;
  const totalExecutions = m?.total_executions ?? 0;
  const overallPassed = metricsPassed === true && casesPassed === true;

  return (
    <div className="flex items-center gap-1.5">
      {score !== null && metricsPassed !== null && (
        <span
          className={cn(PILL, metricsPassed ? PILL_PASS : PILL_FAIL)}
          title="Metrics score"
        >
          <Target className="w-2.5 h-2.5" />
          Metrics {score}%
        </span>
      )}
      {casesPassed !== null && totalExecutions > 0 && (
        <span
          className={cn(PILL, casesPassed ? PILL_PASS : PILL_FAIL)}
          title="Test cases"
        >
          <ListChecks className="w-2.5 h-2.5" />
          Test Cases {passedCount}/{totalExecutions}
        </span>
      )}
      {metricsPassed !== null && casesPassed !== null &&
        (overallPassed ? (
          <CircleCheck className="w-3.5 h-3.5 text-green-400 shrink-0" />
        ) : (
          <CircleX className="w-3.5 h-3.5 text-red-400 shrink-0" />
        ))}
      <Link
        href={UrlGenerator.agentEvalsRuns(agentId)}
        className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors ml-1"
      >
        View
      </Link>
    </div>
  );
};
