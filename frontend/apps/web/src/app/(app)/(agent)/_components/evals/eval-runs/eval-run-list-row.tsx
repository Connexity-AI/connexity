'use client';

import { ListChecks, Target } from 'lucide-react';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { cn } from '@workspace/ui/lib/utils';

import { useRunStream } from '@/app/(app)/(agent)/_hooks/use-run-stream';
import { RunStatus } from '@/client/types.gen';

import { formatAbsoluteLocal, formatLocalShort, formatTimeAgo } from './shared/format-time';
import { RunStatusIcon } from './shared/run-status-icon';
import { roundScore } from './shared/score-utils';

import type { RunPublic } from '@/client/types.gen';

interface EvalRunListRowProps {
  run: RunPublic;
  configName: string;
  repeatIndex?: number;
  isLatestVersion: boolean;
  selected: boolean;
  onToggleSelected: (checked: boolean) => void;
  onOpen: () => void;
}

const PILL_BASE =
  'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-mono tabular-nums';
const PILL_PASS = 'bg-green-500/10 text-green-400 border-green-500/20';
const PILL_FAIL = 'bg-red-500/10 text-red-400 border-red-500/20';

export function EvalRunListRow({
  run,
  configName,
  repeatIndex,
  isLatestVersion,
  selected,
  onToggleSelected,
  onOpen,
}: EvalRunListRowProps) {
  useRunStream({
    runId: run.id,
    agentId: run.agent_id,
    enabled: run.status === RunStatus.PENDING || run.status === RunStatus.RUNNING,
  });

  const metrics = run.aggregate_metrics;
  const isCompleted = run.status === RunStatus.COMPLETED;
  const metricsScore = roundScore(metrics?.weighted_metrics_score_pct);
  const metricsPassed = metrics?.metrics_passed ?? null;
  const casesPassed = metrics?.cases_passed ?? null;
  const passedCount = metrics?.passed_count ?? 0;
  const totalExecutions = metrics?.total_executions ?? 0;
  const toolMode = run.config?.tool_mode ?? 'mock';

  return (
    <li
      className={cn(
        'group grid cursor-pointer grid-cols-[32px_1fr_72px_110px_110px_96px] items-center gap-4 border-b border-border/40 px-5 py-2.5 transition-colors select-none',
        selected ? 'bg-accent/50' : 'hover:bg-accent/20'
      )}
      onClick={onOpen}
    >
      <div
        className="flex items-center justify-start"
        onClick={(e) => e.stopPropagation()}
      >
        <Checkbox
          aria-label={`Select run ${run.name ?? run.id}`}
          checked={selected}
          onCheckedChange={(value) => onToggleSelected(value === true)}
        />
      </div>

      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm text-foreground">
            {run.name ?? configName}
          </span>
          {repeatIndex && repeatIndex > 1 ? (
            <span className="shrink-0 text-[10px] text-muted-foreground">#{repeatIndex}</span>
          ) : null}
          <RunStatusIcon status={run.status} />
        </div>
        <div className="flex min-w-0 items-center gap-2">
          {run.agent_version !== null && run.agent_version !== undefined ? (
            <span className="shrink-0 rounded bg-accent/60 px-1.5 py-0.5 text-[10px] text-muted-foreground">
              v{run.agent_version}
            </span>
          ) : null}
          {isLatestVersion ? (
            <span className="shrink-0 rounded-full border border-green-500/25 bg-green-500/15 px-1.5 py-0.5 text-[10px] text-green-400">
              latest
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex items-center">
        <span
          className={cn(
            'rounded px-1.5 py-0.5 text-[10px]',
            toolMode === 'mock'
              ? 'bg-yellow-500/15 text-yellow-400'
              : 'bg-blue-500/15 text-blue-400'
          )}
        >
          {toolMode === 'mock' ? 'Mock' : 'Live'}
        </span>
      </div>

      <div className="flex items-center">
        {isCompleted && metricsScore !== null && metricsPassed !== null ? (
          <span
            className={cn(PILL_BASE, metricsPassed ? PILL_PASS : PILL_FAIL)}
            title="Metrics score"
          >
            <Target className="w-2.5 h-2.5" />
            {metricsScore}%
          </span>
        ) : (
          <span className="text-xs text-muted-foreground/40 font-mono">—</span>
        )}
      </div>

      <div className="flex items-center">
        {isCompleted && casesPassed !== null ? (
          <span
            className={cn(PILL_BASE, casesPassed ? PILL_PASS : PILL_FAIL)}
            title="Cases passed"
          >
            <ListChecks className="w-2.5 h-2.5" />
            {passedCount}/{totalExecutions}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground/40 font-mono">—</span>
        )}
      </div>

      <div
        className="flex flex-col items-end gap-0.5 text-right text-[10px] text-muted-foreground/60 tabular-nums"
        title={formatAbsoluteLocal(run.created_at)}
      >
        <span>{formatLocalShort(run.created_at)}</span>
        <span className="text-muted-foreground/40">{formatTimeAgo(run.created_at)}</span>
      </div>
    </li>
  );
}
