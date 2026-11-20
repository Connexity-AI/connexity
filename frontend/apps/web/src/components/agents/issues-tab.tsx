'use client';

import { useState } from 'react';
import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { ChevronDown, ChevronRight, OctagonAlert } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { parseTime } from '@/components/calls/format';
import { SeverityLabel } from '@/components/issues/issues-view';

import type { IssueListPublic } from '@/client/types.gen';
import type { FC } from 'react';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
// Severity, Issue, Calls affected, First seen (as in the design).
const COLUMNS = 'grid-cols-[104px_minmax(0,1fr)_120px_96px_16px]';

/** "6 Nov" in the viewer's time zone. */
const day = (iso: string | null | undefined) => {
  if (!iso) return '—';
  const date = parseTime(iso);
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
};

interface Props {
  issues: IssueListPublic;
}

/**
 * The agent's open issues (designs/screens/Connexity Agent Profile.dc.html, Issues tab):
 * the Issues page's list for this agent, period and version, grouped by category. A row
 * opens its issue.
 */
export const IssuesTab: FC<Props> = ({ issues }) => {
  const [closed, setClosed] = useState<Record<string, boolean>>({});
  const open = issues.tiles.open;
  return (
    <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
      <div className="flex items-baseline gap-3 px-6 pt-5 pb-3">
        <h2 className="m-0 text-body font-medium">Issues</h2>
        <span className="text-label text-ink-muted">{open.toLocaleString()} open</span>
      </div>
      {issues.groups.length > 0 ? (
        <>
          <div
            className={cn(
              'grid min-h-10 items-center gap-4 border-t border-hairline px-6 text-label text-ink-secondary',
              COLUMNS
            )}
          >
            <span>Severity</span>
            <span>Issue</span>
            <span>Calls affected</span>
            <span>First seen</span>
            <span />
          </div>
          {issues.groups.map((group) => {
            const key = group.category.value;
            const expanded = !closed[key];
            return (
              <div key={key} className="border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setClosed((state) => ({ ...state, [key]: expanded }))}
                  aria-expanded={expanded}
                  className="flex min-h-12 w-full cursor-pointer items-center gap-2 border-0 bg-transparent px-6 text-left text-body text-ink select-none hover:bg-wash"
                >
                  <span className="flex flex-none text-ink-secondary">
                    {expanded ? (
                      <ChevronDown className="size-4" aria-hidden />
                    ) : (
                      <ChevronRight className="size-4" aria-hidden />
                    )}
                  </span>
                  <span>{group.category.label}</span>
                  <span className="text-label text-ink-secondary">{group.issue_count}</span>
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
                          'grid min-h-11 items-center gap-4 px-6 text-body text-ink no-underline hover:bg-wash',
                          COLUMNS
                        )}
                      >
                        <span className="flex">
                          <SeverityLabel severity={issue.severity} />
                        </span>
                        <span className="py-2.5 text-pretty">{issue.title}</span>
                        <span className="text-label">{issue.calls_affected.toLocaleString()}</span>
                        <span className="text-label text-ink-secondary">
                          {day(issue.first_seen_at)}
                        </span>
                        <ChevronRight className="size-4 text-ink-muted" aria-hidden />
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {issues.truncated && (
            <div className="border-t border-hairline px-6 py-3 text-label text-ink-secondary">
              Showing the worst of {issues.total.toLocaleString()}; the Issues page searches and
              filters them all.
            </div>
          )}
        </>
      ) : (
        <div className="border-t border-hairline px-6 pt-4 pb-6 text-ink-secondary">
          No open issues
        </div>
      )}
    </section>
  );
};
