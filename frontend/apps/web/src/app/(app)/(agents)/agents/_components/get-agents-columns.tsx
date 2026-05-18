import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { type ColumnDef } from '@tanstack/react-table';

import {
  platformBadgeClassName,
  platformLabel,
} from '@/app/(app)/(agents)/_components/new-agent-platform-labels';
import { formatTimeAgo } from '@/app/(app)/(agent)/_components/evals/eval-runs/shared/format-time';
import { type AgentRow } from '@/actions/agents';
import { LastEvalCell } from '@/app/(app)/(agents)/agents/_components/last-eval-cell';

function latestPublishedSubtitle(row: AgentRow): string | null {
  const summary = row.latest_published_version;
  if (!summary) {
    return null;
  }
  const versionPart = `v${summary.version}`;
  if (summary.version_name && summary.version_name.trim()) {
    return `${versionPart} · ${summary.version_name}`;
  }
  return versionPart;
}

export const getAgentsColumns = (): ColumnDef<AgentRow>[] => [
  {
    accessorKey: 'name',
    header: 'Name',
    enableSorting: true,
    cell: ({ row }) => {
      const subtitle = latestPublishedSubtitle(row.original);
      return (
        <div className="flex min-w-[100px] max-w-[280px] flex-col gap-0.5">
          <Link
            href={UrlGenerator.agentEdit(row.original.id)}
            className="truncate text-sm text-foreground hover:underline"
          >
            {row.original.name}
          </Link>
          {subtitle ? (
            <span className="truncate text-[11px] text-muted-foreground">{subtitle}</span>
          ) : (
            <span className="text-[11px] text-muted-foreground/50">No published version</span>
          )}
        </div>
      );
    },
  },

  {
    id: 'platform',
    header: 'Platform',
    enableSorting: false,
    cell: ({ row }) => {
      const platform = row.original.platform;
      if (!platform) {
        return <span className="text-xs text-muted-foreground">—</span>;
      }
      return (
        <span className={platformBadgeClassName(platform)}>
          {platformLabel(platform)}
        </span>
      );
    },
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
        {formatTimeAgo(row.original.updated_at)}
      </span>
    ),
  },
];
