'use client';

import { useEffect, useState, useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Calendar, OctagonAlert, Search, TriangleAlert, X } from 'lucide-react';

import { NumberTile } from '@workspace/ui/components/number-tile';
import { PageBar } from '@workspace/ui/components/page-bar';
import { cn } from '@workspace/ui/lib/utils';

import { clock, timeLabel } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';

import type { CallListItemPublic, CallListPublic } from '@/client/types.gen';
import type { FC } from 'react';

const PERIOD_LABELS: Record<string, string> = {
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
};
const RESULT_OPTIONS = [
  { value: 'failed', label: 'Failed' },
  { value: 'degraded', label: 'Degraded' },
  { value: 'clean', label: 'Clean' },
  { value: 'unchecked', label: 'Unchecked' },
];
const COLUMNS = 'grid-cols-[128px_200px_88px_72px_104px_minmax(0,1fr)]';

const duration = (seconds: number | null | undefined) => (seconds == null ? '' : clock(seconds));

const ResultLabel: FC<{ result: CallListItemPublic['result'] }> = ({ result }) => {
  if (result === 'failed')
    return (
      <span className="inline-flex h-[22px] items-center gap-1 rounded-md bg-critical-bg px-2 text-label font-medium text-critical">
        <OctagonAlert className="size-3" aria-hidden />
        Failed
      </span>
    );
  if (result === 'degraded')
    return (
      <span className="inline-flex h-[22px] items-center gap-1 rounded-md bg-warning-bg px-2 text-label font-medium text-warning">
        <TriangleAlert className="size-3" aria-hidden />
        Degraded
      </span>
    );
  return <span className="text-ink-secondary">{result === 'clean' ? 'Clean' : 'Unchecked'}</span>;
};

const worstLine = (call: CallListItemPublic) => {
  const worst = call.worst_finding;
  if (!worst) return '';
  return worst.key ? `${worst.title}: ${worst.key}` : worst.title;
};

interface Props {
  calls: CallListPublic;
  shown: number;
  pageSize: number;
}

/** Calls (designs/screens/Connexity Calls.dc.html). A row opens the single call. */
export const CallsView: FC<Props> = ({ calls, shown, pageSize }) => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [query, setQuery] = useState(params.get('q') ?? '');

  useEffect(() => setQuery(params.get('q') ?? ''), [params]);

  const go = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!('shown' in changes)) next.delete('shown');
    const search = next.toString();
    startTransition(() => router.replace(search ? `${pathname}?${search}` : pathname));
  };

  const agent = params.get('agent') ?? undefined;
  const result = params.get('result') ?? undefined;
  const category = params.get('category') ?? undefined;
  const anyFilter = Boolean(params.get('q') || agent || result || category);
  const clearAll = () =>
    go({ q: undefined, agent: undefined, result: undefined, category: undefined });

  return (
    <div className={cn('flex max-w-[1120px] flex-col gap-6', pending && 'opacity-70')}>
      <PageBar
        title="Calls"
        actions={
          <Picker
            label="Last 30 days"
            value={calls.period}
            options={Object.entries(PERIOD_LABELS).map(([value, label]) => ({ value, label }))}
            onPick={(value) => go({ period: value === '30d' ? undefined : value })}
            icon={<Calendar className="size-4 text-ink-secondary" aria-hidden />}
            align="end"
            clearable={false}
          />
        }
      />

      <div className="grid grid-cols-4 gap-3">
        <NumberTile label="Calls" value={calls.tiles.calls.toLocaleString()} />
        <NumberTile
          label="Failed"
          value={calls.tiles.failed.toLocaleString()}
          severity="critical"
        />
        <NumberTile
          label="Degraded"
          value={calls.tiles.degraded.toLocaleString()}
          severity="warning"
        />
        <NumberTile label="Clean" value={calls.tiles.clean.toLocaleString()} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {calls.issue && (
          <span className="flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-ink-secondary bg-wash pr-1 pl-3 text-body">
            <Link href={UrlGenerator.issue(calls.issue.value)} className="text-ink no-underline">
              {calls.issue.label}
            </Link>
            <button
              type="button"
              title="Remove"
              aria-label="Remove the issue filter"
              onClick={() => go({ issue: undefined })}
              className="flex size-7 items-center justify-center rounded-md border-0 bg-transparent text-ink-secondary hover:text-ink"
            >
              <X className="size-4" aria-hidden />
            </button>
          </span>
        )}
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
            placeholder="Phone number or call ID"
            aria-label="Phone number or call ID"
            className="h-[34px] min-w-0 flex-1 border-0 bg-transparent text-body text-ink outline-none"
          />
        </form>
        <Picker
          label="Agent"
          value={agent}
          options={calls.agents}
          onPick={(value) => go({ agent: value })}
        />
        <Picker
          label="Result"
          value={result}
          options={RESULT_OPTIONS}
          onPick={(value) => go({ result: value })}
        />
        <Picker
          label="Category"
          value={category}
          options={calls.categories}
          onPick={(value) => go({ category: value })}
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
            'grid min-h-10 items-center gap-4 px-6 text-label text-ink-secondary',
            COLUMNS
          )}
        >
          <span>Time</span>
          <span>Agent</span>
          <span>Caller</span>
          <span className="text-right">Duration</span>
          <span>Result</span>
          <span>{calls.issue ? 'Moment' : 'Worst finding'}</span>
        </div>
        {calls.data.map((call) => (
          <Link
            key={call.id}
            href={UrlGenerator.call(call.id, calls.issue ? call.moment?.at_seconds : undefined)}
            className={cn(
              'grid min-h-11 items-center gap-4 border-t border-hairline px-6 text-body text-ink no-underline hover:bg-wash',
              COLUMNS
            )}
          >
            <span className="whitespace-nowrap">{timeLabel(call.started_at)}</span>
            <span className="truncate">{call.agent_name}</span>
            <span className="whitespace-nowrap text-ink-secondary">
              {call.caller_last_four ? `•••• ${call.caller_last_four}` : '—'}
            </span>
            <span className="text-right text-ink-secondary">{duration(call.duration_seconds)}</span>
            <span className="flex">
              <ResultLabel result={call.result} />
            </span>
            {calls.issue ? (
              <span className="whitespace-nowrap text-ink-secondary">
                {call.moment ? `at ${clock(call.moment.at_seconds)}` : ''}
                {call.moment && call.moment.times > 1 && (
                  <span className="text-ink-muted"> · {call.moment.times} times</span>
                )}
              </span>
            ) : (
              <span className="truncate">{worstLine(call)}</span>
            )}
          </Link>
        ))}
        {calls.data.length === 0 && (
          <div className="flex items-center gap-3 border-t border-hairline px-6 py-5 text-ink-secondary">
            No calls match.
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
        {calls.has_more && (
          <div className="flex justify-center border-t border-hairline p-3">
            <button
              type="button"
              onClick={() => go({ shown: String(shown + pageSize) })}
              className="h-9 rounded-lg border border-border-control bg-transparent px-4 text-body text-ink hover:bg-wash"
            >
              Show more
            </button>
          </div>
        )}
      </section>
    </div>
  );
};
