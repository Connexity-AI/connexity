import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { type ColumnDef } from '@tanstack/react-table';
import { format } from 'date-fns';

import { type AgentRow } from '@/actions/agents';

export const getAgentsColumns = (): ColumnDef<AgentRow>[] => [
  {
    accessorKey: 'name',
    header: 'Name',
    enableSorting: true,
    cell: ({ row }) => (
      <Link
        href={UrlGenerator.agent(row.original.id)}
        className="block min-w-[100px] max-w-[250px] truncate text-sm font-medium text-primary hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },

  {
    accessorKey: 'updated_at',
    header: 'Last Update',
    enableSorting: true,
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-sm text-muted-foreground">
        {format(new Date(row.original.updated_at), "MMM d, yyyy 'at' h:mm a")}
      </span>
    ),
  },
];
