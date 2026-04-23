'use client';

import { Suspense, useMemo } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

import { Accordion } from '@workspace/ui/components/ui/accordion';
import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { Skeleton } from '@workspace/ui/components/ui/skeleton';
import { ToggleGroup, ToggleGroupItem } from '@workspace/ui/components/ui/toggle-group';
import { cn } from '@workspace/ui/lib/utils';

import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';
import { useEvalConfigs } from '@/app/(app)/(agent)/_hooks/use-eval-configs';
import { useEvalResultsSelection } from '@/app/(app)/(agent)/_hooks/use-eval-results-selection';
import { useEvalRunDetail, type ResultFilter } from '@/app/(app)/(agent)/_hooks/use-eval-run-detail';
import { useSuspenseTestCases } from '@/app/(app)/(agent)/_hooks/use-test-cases';
import { useTriggerSuggestFixes } from '@/app/(app)/(agent)/_hooks/use-trigger-suggest-fixes';
import { UrlGenerator } from '@/common/url-generator/url-generator';

import { ConversationDrawer } from './conversation-drawer';
import { ConversationResultRow } from './conversation-result-row';
import { EvalRunMetricsBar } from './eval-run-metrics-bar';
import { EvalRunSelectionToolbar } from './eval-run-selection-toolbar';
import { SelectionCheckbox } from './selection-checkbox';
import { RunStatusIcon, runStatusBadgeClasses, runStatusLabel } from './shared/run-status-icon';

import type { RunStatus } from '@/client/types.gen';

interface EvalRunDetailViewProps {
  agentId: string;
  runId: string;
}

export function EvalRunDetailView({ agentId, runId }: EvalRunDetailViewProps) {
  const backHref = UrlGenerator.agentEvalsRuns(agentId);

  return (
    <Suspense fallback={<EvalRunDetailSkeleton backHref={backHref} />}>
      <EvalRunDetailContent agentId={agentId} runId={runId} backHref={backHref} />
    </Suspense>
  );
}

function EvalRunDetailContent({
  agentId,
  runId,
  backHref,
}: EvalRunDetailViewProps & { backHref: string }) {
  const { data: configsData } = useEvalConfigs(agentId);
  const { data: testCasesData } = useSuspenseTestCases(agentId);
  const { data: agent } = useAgent(agentId);
  const configs = configsData?.data ?? [];
  const testCases = testCasesData?.data ?? [];

  const {
    run,
    results,
    filteredResults,
    configName,
    testCaseById,
    passedCount,
    failedCount,
    filter,
    setFilter,
    drawerResultId,
    setDrawerResultId,
    drawerResult,
  } = useEvalRunDetail({ runId, configs, testCases });

  const filteredIds = useMemo(() => filteredResults.map((r) => r.id), [filteredResults]);
  const { selectedIds, allSelected, someSelected, toggleRow, toggleAll, clear } =
    useEvalResultsSelection(filteredIds);
  const hasSelection = selectedIds.size > 0;

  const handleSuggestFixes = useTriggerSuggestFixes({
    agentId,
    runId,
    results,
    selectedIds,
    testCaseById,
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <BackButton href={backHref} />
          <Separator orientation="vertical" className="h-4" />
          <div className="flex min-w-0 items-center gap-2 text-sm">
            <span className="truncate text-foreground">{configName}</span>
            {run.agent_version !== null && run.agent_version !== undefined ? (
              <span className="shrink-0 rounded bg-accent/60 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                v{run.agent_version}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px]',
              runStatusBadgeClasses(run.status as RunStatus)
            )}
          >
            <RunStatusIcon status={run.status} />
            {runStatusLabel(run.status as RunStatus)}
          </span>
        </div>
      </div>

      <EvalRunMetricsBar run={run} status={run.status as RunStatus} />

      {hasSelection ? (
        <EvalRunSelectionToolbar
          selectedCount={selectedIds.size}
          allSelected={allSelected}
          someSelected={someSelected}
          onToggleAll={toggleAll}
          onSuggestFixes={handleSuggestFixes}
          onClear={clear}
        />
      ) : (
        <div className="flex h-10 shrink-0 items-center gap-4 border-b border-border px-5 py-2">
          <SelectionCheckbox
            checked={false}
            onCheckedChange={(checked) => toggleAll(checked === true)}
            aria-label="Select all"
            disabled={filteredIds.length === 0}
          />
          <ToggleGroup
            type="single"
            value={filter}
            onValueChange={(v) => {
              if (v) setFilter(v as ResultFilter);
            }}
            className="gap-1"
          >
            <ToggleGroupItem
              value="all"
              className="h-6 px-2 text-[11px] data-[state=on]:bg-accent/60"
            >
              All ({results.length})
            </ToggleGroupItem>
            <ToggleGroupItem
              value="passed"
              className="h-6 px-2 text-[11px] data-[state=on]:bg-green-500/15 data-[state=on]:text-green-400"
            >
              Passed ({passedCount})
            </ToggleGroupItem>
            <ToggleGroupItem
              value="failed"
              className="h-6 px-2 text-[11px] data-[state=on]:bg-red-500/15 data-[state=on]:text-red-400"
            >
              Failed ({failedCount})
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {filteredResults.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
            <p className="text-sm text-muted-foreground">
              {results.length === 0
                ? 'No test case results for this run yet.'
                : `No ${filter} results.`}
            </p>
          </div>
        ) : (
          <Accordion type="multiple" className="w-full">
            {filteredResults.map((result) => {
              const testCase = testCaseById.get(result.test_case_id);
              return (
                <ConversationResultRow
                  key={result.id}
                  result={result}
                  testCaseName={testCase?.name ?? 'Unknown test case'}
                  tags={testCase?.tags}
                  difficulty={testCase?.difficulty}
                  onOpenTrace={() => setDrawerResultId(result.id)}
                  selected={selectedIds.has(result.id)}
                  onSelectChange={toggleRow}
                />
              );
            })}
          </Accordion>
        )}
      </div>

      <ConversationDrawer
        open={drawerResultId !== null}
        onOpenChange={(open) => {
          if (!open) setDrawerResultId(null);
        }}
        result={drawerResult}
        testCaseName={
          drawerResult
            ? testCaseById.get(drawerResult.test_case_id)?.name ?? 'Unknown test case'
            : ''
        }
        agentName={agent?.name ?? null}
      />
    </div>
  );
}

function BackButton({ href }: { href: string }) {
  return (
    <Button
      asChild
      variant="ghost"
      size="sm"
      className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
    >
      <Link href={href}>
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </Link>
    </Button>
  );
}

function EvalRunDetailSkeleton({ backHref }: { backHref: string }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3">
        <div className="flex items-center gap-3">
          <BackButton href={backHref} />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-border px-5 py-2">
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-20" />
      </div>
      <ul>
        {Array.from({ length: 6 }).map((_, i) => (
          <li
            key={i}
            className="grid grid-cols-[32px_24px_1fr_auto_auto_auto] items-center gap-3 border-b border-border/40 px-5 py-3"
          >
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-3.5 w-56" />
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-6 w-14" />
            <Skeleton className="h-3 w-14" />
          </li>
        ))}
      </ul>
    </div>
  );
}
