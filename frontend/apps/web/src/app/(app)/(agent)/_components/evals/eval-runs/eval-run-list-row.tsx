'use client';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { cn } from '@workspace/ui/lib/utils';

import { useRunStream } from '@/app/(app)/(agent)/_hooks/use-run-stream';
import { RunStatus } from '@/client/types.gen';

import { formatTimeAgo } from './shared/format-time';
import { RunStatusIcon } from './shared/run-status-icon';
import { ScoreBar } from './shared/score-bar';
import { roundScore, scoreColor } from './shared/score-utils';

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
  const avgScore = roundScore(metrics?.avg_overall_score);
  const passRate =
    metrics && metrics.total_executions > 0
      ? (metrics.passed_count / metrics.total_executions) * 100
      : null;
  const toolMode = run.config?.tool_mode ?? 'mock';

  const scoreText = scoreColor(avgScore);
  const passRateColor = scoreColor(passRate);

  return (
    <li
      className={cn(
        'group grid cursor-pointer grid-cols-[32px_1fr_72px_110px_110px_96px] items-center gap-3 border-b border-border/40 px-5 py-3 transition-colors select-none',
        selected ? 'bg-accent/50' : 'hover:bg-accent/25'
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

      <div className="flex flex-col gap-1">
        <span className={cn('font-mono text-xs tabular-nums', scoreText.text)}>
          {avgScore === null ? '—' : `${avgScore}/100`}
        </span>
        <ScoreBar value={avgScore} />
      </div>

      <div className="flex flex-col gap-1">
        <span className={cn('font-mono text-xs tabular-nums', passRateColor.text)}>
          {metrics
            ? `${metrics.passed_count}/${metrics.total_executions}`
            : '—'}
        </span>
        <ScoreBar value={passRate} />
      </div>

      <div className="text-right text-[10px] text-muted-foreground/60 tabular-nums">
        {formatTimeAgo(run.created_at)}
      </div>
    </li>
  );
}
