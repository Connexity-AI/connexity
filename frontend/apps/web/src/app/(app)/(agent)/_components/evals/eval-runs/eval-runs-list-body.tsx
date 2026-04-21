'use client';

import { EvalRunListRow } from './eval-run-list-row';

import type { RunConfigGroup } from '@/app/(app)/(agent)/_hooks/use-eval-runs-view';
import type { EvalConfigPublic, RunPublic } from '@/client/types.gen';

interface EvalRunsListBodyProps {
  groupedRuns: RunConfigGroup[] | null;
  sortedRuns: RunPublic[];
  configById: Map<string, EvalConfigPublic>;
  repeatIndexByRun: Map<string, number>;
  latestVersion: number | null;
  checkedIds: Set<string>;
  onToggleOne: (id: string, checked: boolean) => void;
  onOpenRun: (runId: string) => void;
}

export function EvalRunsListBody(props: EvalRunsListBodyProps) {
  if (props.groupedRuns) {
    return <GroupedRuns {...props} groupedRuns={props.groupedRuns} />;
  }
  return <FlatRuns {...props} />;
}

type RowContext = Omit<EvalRunsListBodyProps, 'groupedRuns' | 'sortedRuns'>;

function GroupedRuns({
  groupedRuns,
  ...ctx
}: { groupedRuns: RunConfigGroup[] } & RowContext) {
  return (
    <ul>
      {groupedRuns.map(({ configId, configName, items }) => (
        <li key={configId}>
          <GroupHeader name={configName} count={items.length} />
          <ul>
            {items.map((run) => (
              <RunRow key={run.id} run={run} {...ctx} />
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

function FlatRuns({
  sortedRuns,
  ...ctx
}: { sortedRuns: RunPublic[] } & RowContext) {
  return (
    <ul>
      {sortedRuns.map((run) => (
        <RunRow key={run.id} run={run} {...ctx} />
      ))}
    </ul>
  );
}

function GroupHeader({ name, count }: { name: string; count: number }) {
  return (
    <div className="sticky top-0 z-[5] border-b border-border bg-background/95 px-5 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/70 backdrop-blur">
      {name}
      <span className="ml-2 text-muted-foreground/50">
        {count} {count === 1 ? 'run' : 'runs'}
      </span>
    </div>
  );
}

function RunRow({
  run,
  configById,
  repeatIndexByRun,
  latestVersion,
  checkedIds,
  onToggleOne,
  onOpenRun,
}: { run: RunPublic } & RowContext) {
  return (
    <EvalRunListRow
      run={run}
      configName={configById.get(run.eval_config_id)?.name ?? 'Unknown config'}
      repeatIndex={repeatIndexByRun.get(run.id)}
      isLatestVersion={
        latestVersion !== null && run.agent_version === latestVersion
      }
      selected={checkedIds.has(run.id)}
      onToggleSelected={(checked) => onToggleOne(run.id, checked)}
      onOpen={() => onOpenRun(run.id)}
    />
  );
}
