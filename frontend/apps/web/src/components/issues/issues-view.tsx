'use client';

import { useEffect, useState, useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import {
  Calendar,
  ChevronDown,
  ChevronRight,
  OctagonAlert,
  RotateCcw,
  Search,
  TriangleAlert,
} from 'lucide-react';

import { NumberTile } from '@workspace/ui/components/number-tile';
import { PageBar } from '@workspace/ui/components/page-bar';
import { cn } from '@workspace/ui/lib/utils';

import { parseTime } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';

import type { IssueGroupPublic, IssueListItemPublic, IssueListPublic } from '@/client/types.gen';
import type { FC } from 'react';

const PERIOD_LABELS: Record<string, string> = {
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
};
const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'warning', label: 'Warning' },
];
const STATUS_OPTIONS = [
  { value: 'open', label: 'Open' },
  { value: 'reopened', label: 'Reopened' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'archived', label: 'Archived' },
];
// The design's columns without Milestone: there is no roadmap yet (rule 14).
const COLUMNS = 'grid-cols-[minmax(0,1fr)_152px_80px_112px_136px_104px]';

const count = (n: number, one: string, many: string) =>
  `${n.toLocaleString()} ${n === 1 ? one : many}`;

/** "38 calls · 3%" of the agent's calls in the period. */
const share = (issue: IssueListItemPublic) => {
  if (!issue.calls_total) return '';
  const pct = (issue.calls_affected / issue.calls_total) * 100;
  return `${pct > 0 && pct < 1 ? pct.toFixed(1) : Math.round(pct)}%`;
};

/** "12 minutes ago", "3 hours ago", "Yesterday", "4 days ago". */
export const lastSeen = (iso: string | null | undefined) => {
  if (!iso) return '—';
  const minutes = Math.max(0, Math.round((Date.now() - parseTime(iso).getTime()) / 60000));
  if (minutes < 60) return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
  if (minutes < 1440) {
    const hours = Math.round(minutes / 60);
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
  }
  if (minutes < 2880) return 'Yesterday';
  return `${Math.floor(minutes / 1440)} days ago`;
};

const SeverityLabel: FC<{ severity: IssueListItemPublic['severity'] }> = ({ severity }) =>
  severity === 'critical' ? (
    <span className="inline-flex h-[22px] items-center gap-1 rounded-md bg-critical-bg px-2 text-label font-medium text-critical">
      <OctagonAlert className="size-3.5" aria-hidden />
      Critical
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-label text-warning">
      <TriangleAlert className="size-3.5" aria-hidden />
      Warning
    </span>
  );

const StatusLabel: FC<{ issue: IssueListItemPublic }> = ({ issue }) => {
  if (issue.state === 'reopened')
    return (
      <span className="inline-flex h-[22px] items-center gap-1 rounded-md bg-accent-ink px-2 font-medium text-on-accent">
        <RotateCcw className="size-3" aria-hidden />
        Reopened
      </span>
    );
  if (issue.state === 'resolved')
    return (
      <span className="text-passed">
        {issue.resolved_version ? `Resolved in version ${issue.resolved_version}` : 'Resolved'}
      </span>
    );
  if (issue.state === 'archived') return <span className="text-ink-secondary">Archived</span>;
  return <span>Open</span>;
};

const Group: FC<{ group: IssueGroupPublic; expanded: boolean; onToggle: () => void }> = ({
  group,
  expanded,
  onToggle,
}) => (
  <div className="border-t border-hairline">
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={expanded}
      className="flex min-h-12 w-full cursor-pointer select-none items-center gap-2 border-0 bg-transparent px-6 text-left text-body text-ink hover:bg-wash"
    >
      <span className="flex flex-none text-ink-secondary">
        {expanded ? (
          <ChevronDown className="size-4" aria-hidden />
        ) : (
          <ChevronRight className="size-4" aria-hidden />
        )}
      </span>
      <span>{group.category.label}</span>
      <span className="text-label text-ink-secondary">
        {count(group.issue_count, 'issue', 'issues')} ·{' '}
        {count(group.calls_affected, 'call', 'calls')}
      </span>
      {group.critical > 0 && (
        <span className="inline-flex h-[22px] flex-none items-center gap-1 rounded-md bg-critical-bg px-1.5 text-label font-medium text-critical">
          <OctagonAlert className="size-3.5" aria-hidden />
          {group.critical} critical
        </span>
      )}
    </button>
    {expanded && (
      <div className="pb-2">
        {group.issues.map((issue) => (
          <Link
            key={issue.id}
            href={UrlGenerator.issue(issue.id)}
            title="Open the issue"
            className={cn(
              'grid min-h-11 items-center gap-4 pr-6 pl-12 text-body text-ink no-underline hover:bg-wash',
              COLUMNS
            )}
          >
            <span className="py-2.5 text-pretty">{issue.title}</span>
            <span className="truncate text-label text-ink-secondary">{issue.agent_name}</span>
            <span className="flex">
              <SeverityLabel severity={issue.severity} />
            </span>
            <span className="whitespace-nowrap text-label">
              {count(issue.calls_affected, 'call', 'calls')}
              {share(issue) && <span className="text-ink-muted"> · {share(issue)}</span>}
            </span>
            <span className="flex text-label">
              <StatusLabel issue={issue} />
            </span>
            <span className="whitespace-nowrap text-label text-ink-secondary">
              {lastSeen(issue.last_seen_at)}
            </span>
          </Link>
        ))}
      </div>
    )}
  </div>
);

interface Props {
  issues: IssueListPublic;
}

/**
 * Issues (designs/screens/Connexity Issues.dc.html). A row opens its issue. There is no
 * Milestone column until the roadmap exists (rule 14).
 */
export const IssuesView: FC<Props> = ({ issues }) => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [query, setQuery] = useState(params.get('q') ?? '');
  const [open, setOpen] = useState<Record<string, boolean>>({});

  useEffect(() => setQuery(params.get('q') ?? ''), [params]);

  const go = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    const search = next.toString();
    startTransition(() => router.replace(search ? `${pathname}?${search}` : pathname));
  };

  const searching = Boolean(params.get('q'));
  const agent = params.get('agent') ?? undefined;
  const category = params.get('category') ?? undefined;
  const severity = params.get('severity') ?? undefined;
  const anyFilter = Boolean(searching || agent || category || severity || issues.status !== 'open');
  const clearAll = () =>
    go({
      q: undefined,
      agent: undefined,
      category: undefined,
      severity: undefined,
      status: undefined,
    });
  const { tiles } = issues;

  return (
    <div className={cn('flex max-w-[1120px] flex-col gap-6', pending && 'opacity-70')}>
      <PageBar
        title="Issues"
        actions={
          <Picker
            label="Last 30 days"
            value={issues.period}
            options={Object.entries(PERIOD_LABELS).map(([value, label]) => ({ value, label }))}
            onPick={(value) => go({ period: value === '30d' ? undefined : value })}
            icon={<Calendar className="size-4 text-ink-secondary" aria-hidden />}
            align="end"
            clearable={false}
          />
        }
      />

      <div className="grid grid-cols-5 gap-3">
        <NumberTile label="Open" value={tiles.open.toLocaleString()} />
        <NumberTile label="Critical" value={tiles.critical.toLocaleString()} severity="critical" />
        <NumberTile label="Reopened" value={tiles.reopened.toLocaleString()} />
        <NumberTile label="Resolved" value={tiles.resolved.toLocaleString()} />
        <NumberTile
          label="Calls affected"
          value={tiles.calls_affected.toLocaleString()}
          unit={`of ${tiles.calls.toLocaleString()}`}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <form
          role="search"
          className="flex h-9 w-[280px] items-center gap-2 rounded-lg border border-border-control bg-surface-1 px-3"
          onSubmit={(event) => {
            event.preventDefault();
            go({ q: query.trim() || undefined });
          }}
        >
          <Search className="size-4 flex-none text-ink-secondary" aria-hidden />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onBlur={() => {
              if ((params.get('q') ?? '') !== query.trim()) go({ q: query.trim() || undefined });
            }}
            placeholder="Issue title or ID"
            aria-label="Issue title or ID"
            className="h-[34px] min-w-0 flex-1 border-0 bg-transparent text-body text-ink outline-none"
          />
        </form>
        <Picker
          label="All agents"
          value={agent}
          options={issues.agents}
          onPick={(value) => go({ agent: value })}
        />
        <Picker
          label="Any category"
          value={category}
          options={issues.categories}
          onPick={(value) => go({ category: value })}
        />
        <Picker
          label="Any severity"
          value={severity}
          options={SEVERITY_OPTIONS}
          onPick={(value) => go({ severity: value })}
        />
        <Picker
          label="Open"
          value={issues.status}
          options={STATUS_OPTIONS}
          onPick={(value) => go({ status: value === 'open' ? undefined : value })}
          clearable={false}
          highlighted={issues.status !== 'open'}
        />
        {anyFilter && (
          <button
            type="button"
            onClick={clearAll}
            className="h-9 border-0 bg-transparent px-2 text-body text-ink-secondary underline"
          >
            Clear
          </button>
        )}
      </div>

      <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
        <div
          className={cn(
            'grid min-h-10 items-center gap-4 pr-6 pl-12 text-label text-ink-secondary',
            COLUMNS
          )}
        >
          <span>Issue</span>
          <span>Agent</span>
          <span>Severity</span>
          <span>Calls affected</span>
          <span>Status</span>
          <span>Last seen</span>
        </div>
        {issues.groups.map((group) => {
          const key = group.category.value;
          const expanded = open[key] ?? searching;
          return (
            <Group
              key={key}
              group={group}
              expanded={expanded}
              onToggle={() => setOpen((state) => ({ ...state, [key]: !expanded }))}
            />
          );
        })}
        {issues.groups.length === 0 && (
          <div className="flex items-center gap-3 border-t border-hairline px-6 py-5 text-ink-secondary">
            No issues match.
            {anyFilter && (
              <button
                type="button"
                onClick={clearAll}
                className="border-0 bg-transparent p-0 text-body text-ink underline"
              >
                Clear the search and filters
              </button>
            )}
          </div>
        )}
        {issues.truncated && (
          <div className="border-t border-hairline px-6 py-3 text-label text-ink-secondary">
            Showing the worst{' '}
            {count(
              issues.groups.reduce((n, g) => n + g.issue_count, 0),
              'issue',
              'issues'
            )}{' '}
            of {issues.total.toLocaleString()}. Search or filter to narrow the list.
          </div>
        )}
      </section>
    </div>
  );
};
