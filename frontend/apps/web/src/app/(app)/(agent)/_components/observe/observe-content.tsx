'use client';

import { useMemo } from 'react';
import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { callsObserveParser } from '@/common/url-generator/parsers';
import { RefreshCw } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { cn } from '@workspace/ui/lib/utils';

import { DeleteTestCasesDialog } from '@/app/(app)/(agent)/_components/evals/test-cases/delete-test-cases-dialog';
import { useEnvironments } from '@/app/(app)/(agent)/_hooks/use-environments';
import { DataTable } from '@/components/common/data-table/data-table';
import { TablePagination } from '@/components/common/data-table/table-pagination';

import { DateRangePicker } from './date-range-picker';
import { getCallsColumns } from './get-calls-columns';
import { ObserveDrawer } from './observe-drawer';
import { ObserveTableSkeleton } from './observe-table-skeleton';
import { useObserveCalls } from './use-observe-calls';
import { useObserveDrawerState } from './use-observe-drawer-state';

interface ObserveContentProps {
  agentId: string;
}

export function ObserveContent({ agentId }: ObserveContentProps) {
  const { data: environmentsData } = useEnvironments(agentId);

  const calls = useObserveCalls(agentId);
  const drawer = useObserveDrawerState({ agentId, calls: calls.rows });

  const columns = useMemo(
    () =>
      getCallsColumns({
        testCasesByCallId: drawer.testCasesByCallId,
        onTestCaseClick: drawer.onTestCaseClick,
      }),
    [drawer.testCasesByCallId, drawer.onTestCaseClick],
  );

  const hasRetellEnvironment = (environmentsData?.data ?? []).some(
    (env) => env.platform === 'retell',
  );

  if (calls.isLoading) {
    return <ObserveTableSkeleton />;
  }

  if (!hasRetellEnvironment) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-10 text-center">
        <p className="text-sm text-muted-foreground">
          No environment connected yet. Go to the{' '}
          <Link
            href={UrlGenerator.agentDeploy(agentId)}
            className="text-foreground underline underline-offset-2"
          >
            Deploy tab
          </Link>{' '}
          and add an environment to start observing calls.
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/40 px-5 py-3">
        <div className="text-xs text-muted-foreground">
          <span className="text-foreground tabular-nums">{calls.totalCount}</span>{' '}
          {calls.totalCount === 1 ? 'call' : 'calls'}
        </div>
        <div className="flex items-center gap-3">
          <DateRangePicker value={calls.dateRange} onChange={calls.onDateRangeChange} />

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={calls.onRefresh}
            disabled={calls.isRefreshPending}
            className="h-auto gap-2 rounded-lg border-border px-3 py-1.5 text-[11px] font-normal text-muted-foreground hover:bg-accent/30"
          >
            <RefreshCw
              className={cn('h-3.5 w-3.5 shrink-0', {
                'animate-spin': calls.isRefreshPending,
              })}
            />
            Refresh
          </Button>
        </div>
      </div>

      <div
        className={cn('flex-1 overflow-auto transition-opacity duration-200', {
          'pointer-events-none opacity-60': calls.isFetching,
        })}
      >
        <DataTable
          columns={columns}
          data={calls.rows}
          onRowClick={drawer.onRowClick}
          emptyState={
            <p className="text-sm text-muted-foreground">
              No calls yet. Click Refresh to fetch from Retell.
            </p>
          }
          footer={
            <TablePagination totalCount={calls.totalCount} parser={callsObserveParser} />
          }
        />
      </div>

      <ObserveDrawer
        agentId={agentId}
        call={drawer.selectedCall}
        testCase={drawer.selectedTestCase}
        rightPanelMode={drawer.rightPanelMode}
        onClose={drawer.onCloseDrawer}
        onCloseRightPanel={drawer.onCloseRightPanel}
        onCreateTestCaseManual={drawer.onCreateTestCaseManual}
        onCreateTestCaseAi={drawer.onCreateTestCaseAi}
        onRequestDeleteTestCase={drawer.deletion.requestSingle}
      />

      <DeleteTestCasesDialog
        open={drawer.deletion.dialogOpen}
        onOpenChange={drawer.deletion.onOpenChange}
        testCases={drawer.deletion.targets}
        onConfirm={drawer.deletion.confirm}
        isPending={drawer.deletion.isPending}
      />
    </div>
  );
}
