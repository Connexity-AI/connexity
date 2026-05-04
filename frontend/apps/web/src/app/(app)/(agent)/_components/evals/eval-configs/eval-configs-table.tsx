'use client';

import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { FlaskConical, Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { cn } from '@workspace/ui/lib/utils';

import {
  readJudgeCasesThreshold,
  readJudgeMetricsThreshold,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import { RunEvalConfigButton } from '@/app/(app)/(agent)/_components/evals/run-eval-config-button';
import { useEvalConfigs } from '@/app/(app)/(agent)/_hooks/use-eval-configs';

import type { EvalConfigPublic } from '@/client/types.gen';

function formatDate(iso: string) {
  const date = new Date(iso);
  return date.toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface EvalConfigsTableProps {
  agentId: string;
}

export function EvalConfigsTable({ agentId }: EvalConfigsTableProps) {
  const { data } = useEvalConfigs(agentId);

  const configs = data?.data ?? [];

  if (configs.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-accent/40">
          <FlaskConical className="h-6 w-6 text-muted-foreground/50" />
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="text-sm text-foreground">No eval configs yet</p>
          <p className="max-w-xs text-xs text-muted-foreground">
            Pick test cases on the Test Cases tab and create an eval config to define how they run.
          </p>
        </div>
        <Button asChild size="sm" className="gap-1.5">
          <Link href={UrlGenerator.agentEvalsTestCases(agentId)}>
            <Plus className="h-3.5 w-3.5" />
            Go to Test Cases
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
      <Header agentId={agentId} count={configs.length} />
      <div className="flex-1 overflow-auto">
        <ColumnHeaders />
        <ul>
          {configs.map((config) => (
            <Row key={config.id} agentId={agentId} config={config} />
          ))}
        </ul>
      </div>
    </div>
  );
}

function Header({ agentId, count }: { agentId: string; count: number }) {
  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-5 py-2.5">
      <p className="text-xs text-muted-foreground">
        {count} eval {count === 1 ? 'config' : 'configs'}
      </p>
      <Button asChild size="sm" className="h-7 gap-1.5 text-xs">
        <Link href={UrlGenerator.agentEvalsCreate(agentId)}>
          <Plus className="h-3 w-3" />
          New Eval Config
        </Link>
      </Button>
    </div>
  );
}

const ROW_GRID = 'grid-cols-[1fr_100px_120px_120px_110px_110px_180px_80px]';

function ColumnHeaders() {
  return (
    <div
      className={cn(
        'sticky top-0 z-10 grid items-center gap-4 border-b border-border bg-background px-5 py-2 text-[10px] uppercase tracking-wider text-muted-foreground/60',
        ROW_GRID
      )}
    >
      <span>Name</span>
      <span>Cases</span>
      <span>Total Runs</span>
      <span>Tool Calls</span>
      <span>Metrics %</span>
      <span>Cases %</span>
      <span>Created</span>
      <span />
    </div>
  );
}

function Row({ agentId, config }: { agentId: string; config: EvalConfigPublic }) {
  const toolMode = config.config?.tool_mode ?? 'mock';
  const metricsThreshold = readJudgeMetricsThreshold(config.config?.judge);
  const casesThreshold = readJudgeCasesThreshold(config.config?.judge);
  return (
    <li
      className={cn(
        'group relative grid items-center gap-4 border-b border-border/40 px-5 py-2.5 hover:bg-accent/20',
        ROW_GRID
      )}
    >
      <Link
        href={UrlGenerator.agentEvalsConfigDetail(agentId, config.id)}
        className="absolute inset-0"
        aria-label={`Open ${config.name}`}
      />
      <span className="pointer-events-none relative truncate text-sm">{config.name}</span>
      <span className="pointer-events-none relative font-mono text-xs tabular-nums text-muted-foreground">
        {config.test_case_count ?? 0}
      </span>
      <span className="pointer-events-none relative font-mono text-xs tabular-nums text-muted-foreground">
        {config.total_runs ?? 0}
      </span>
      <span
        className={cn(
          'pointer-events-none relative w-fit rounded px-1.5 py-0.5 text-[10px]',
          toolMode === 'mock' ? 'bg-yellow-500/15 text-yellow-400' : 'bg-blue-500/15 text-blue-400'
        )}
      >
        {toolMode === 'mock' ? 'Mock' : 'Live'}
      </span>
      <span className="pointer-events-none relative font-mono text-xs tabular-nums text-violet-400">
        {metricsThreshold}%
      </span>

      <span className="pointer-events-none relative font-mono text-xs tabular-nums text-emerald-400">
        {casesThreshold}%
      </span>

      <span className="pointer-events-none relative text-xs text-muted-foreground">
        {formatDate(config.created_at)}
      </span>
      <div className="relative flex justify-end">
        <RunEvalConfigButton agentId={agentId} evalConfigId={config.id} variant="row" />
      </div>
    </li>
  );
}
