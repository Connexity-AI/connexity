'use client';

import { Clock, FlaskConical } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import type { ColumnDef } from '@tanstack/react-table';

import type { CallRow } from '@/actions/calls';
import type { TestCasePublic } from '@/client/types.gen';

function formatCallDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

interface GetCallsColumnsArgs {
  testCasesByCallId: Map<string, TestCasePublic[]>;
  onTestCaseClick: (call: CallRow, testCase: TestCasePublic) => void;
}

export const getCallsColumns = ({
  testCasesByCallId,
  onTestCaseClick,
}: GetCallsColumnsArgs): ColumnDef<CallRow>[] => [
  {
    accessorKey: 'started_at',
    header: 'Date',
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex min-w-0 items-center gap-2">
        <span className="truncate text-sm text-foreground tabular-nums">
          {formatCallDate(row.original.started_at)}
        </span>
        {row.original.is_new ? (
          <span className="inline-flex items-center rounded border border-violet-500/25 bg-violet-500/15 px-1.5 py-px align-middle text-[9px] text-violet-300">
            New
          </span>
        ) : null}
      </div>
    ),
  },
  {
    accessorKey: 'duration_seconds',
    header: 'Duration',
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex items-center gap-1.5 text-xs tabular-nums text-muted-foreground">
        <Clock className="h-3 w-3" />
        {formatDuration(row.original.duration_seconds)}
      </div>
    ),
  },
  {
    accessorKey: 'test_case_count',
    header: 'Test Cases',
    enableSorting: false,
    cell: ({ row }) => {
      const call = row.original;
      const items = testCasesByCallId.get(call.id) ?? [];

      if (items.length === 0) {
        return <span className="text-[10px] text-muted-foreground/30">—</span>;
      }

      return (
        <div className="flex flex-col gap-1">
          {items.map((tc) => (
            <Button
              key={tc.id}
              type="button"
              variant="ghost"
              size="sm"
              onClick={(event) => {
                event.stopPropagation();
                onTestCaseClick(call, tc);
              }}
              className="group/tc h-auto max-w-[200px] justify-start gap-1.5 rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-left text-[10px] font-normal text-emerald-400 transition-all [&_svg]:size-2.5 hover:border-emerald-500/35 hover:bg-emerald-500/20 hover:text-emerald-400"
            >
              <FlaskConical className="shrink-0" />
              <span className="truncate">{tc.name}</span>
            </Button>
          ))}
        </div>
      );
    },
  },
];
