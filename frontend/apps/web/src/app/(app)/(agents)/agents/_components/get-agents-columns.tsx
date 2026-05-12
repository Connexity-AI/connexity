import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { type ColumnDef } from '@tanstack/react-table';
import { format } from 'date-fns';

import { type AgentRow } from '@/actions/agents';
import { LastEvalCell } from '@/app/(app)/(agents)/agents/_components/last-eval-cell';

export const getAgentsColumns = (): ColumnDef<AgentRow>[] => [
  {
    accessorKey: 'name',
    header: 'Name',
    enableSorting: true,
    cell: ({ row }) => (
      <Link
        href={UrlGenerator.agentEdit(row.original.id)}
        className="block min-w-[100px] max-w-[250px] truncate text-sm text-foreground hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },

  {
    id: 'last_eval',
    header: 'Last Eval',
    enableSorting: false,
    cell: ({ row }) => <LastEvalCell lastEval={row.original.last_eval} />,
  },

  {
    accessorKey: 'updated_at',
    header: 'Last Update',
    enableSorting: true,
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-xs text-muted-foreground tabular-nums">
        {format(new Date(row.original.updated_at), "MMM d, yyyy 'at' h:mm a")}
      </span>
    ),
  },
];
