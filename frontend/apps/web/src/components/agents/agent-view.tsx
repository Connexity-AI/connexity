'use client';

import { useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { ArrowLeft, Calendar, Layers, OctagonAlert } from 'lucide-react';

import { NumberTile } from '@workspace/ui/components/number-tile';
import { cn } from '@workspace/ui/lib/utils';

import { PLATFORMS, TYPES } from '@/components/agents/agents-view';
import { IssuesTab } from '@/components/agents/issues-tab';
import { SpecTab } from '@/components/agents/spec-tab';
import { TestsTab } from '@/components/agents/tests-tab';
import { parseTime } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';

import type {
  AgentPagePublic,
  IssueListPublic,
  SpecPublic,
  TestsTabPublic,
} from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

const PERIOD_LABELS: Record<string, string> = {
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
};
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "6 Nov" in the viewer's time zone. */
const dayLabel = (iso: string) => {
  const date = parseTime(iso);
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
};

/** "6 Nov" for a UTC calendar day ("2026-11-06"). */
const calendarDay = (day: string) => {
  const [, month, date] = day.split('-').map(Number);
  return `${date} ${MONTHS[(month ?? 1) - 1]}`;
};

/** "Retell · Conversational flow · version 14, live since 6 Nov" */
const caption = (agent: AgentPagePublic) =>
  [
    agent.platform ? PLATFORMS[agent.platform] : null,
    agent.type ? TYPES[agent.type] : null,
    agent.live_version
      ? `version ${agent.live_version}${agent.live_since ? `, live since ${dayLabel(agent.live_since)}` : ''}`
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

const Detail: FC<{ label: string; children: ReactNode }> = ({ label, children }) => (
  <>
    <span className="text-label text-ink-secondary">{label}</span>
    <span className="text-body text-ink">{children}</span>
  </>
);

const Axis: FC<{ value: string; className: string }> = ({ value, className }) => (
  <div className={cn('absolute right-0 left-0 flex items-center gap-2', className)}>
    <span className="w-8 text-right text-label leading-none text-ink-muted">{value}</span>
    <span className="flex-1 border-t border-hairline" />
  </div>
);

type Day = AgentPagePublic['latency_days'][number];

/** The line through each day's value in a 0..100 box; days without one are stepped
 * over, so calls a few days apart still draw a line. */
const linePath = (values: (number | null)[], top: number) =>
  values
    .map((v, i) =>
      v == null
        ? null
        : `${(((i + 0.5) / (values.length || 1)) * 100).toFixed(2)} ${(100 - (Math.min(v, top) / top) * 100).toFixed(2)}`
    )
    .filter((point): point is string => point != null)
    .map((point, i) => `${i ? 'L' : 'M'}${point}`)
    .join(' ');

/** One panel of the chart: a line through each day's value with a dot on each, its
 * axis, the picked version's days shaded and the version marks. */
const Panel: FC<{
  agent: AgentPagePublic;
  label: string;
  values: (number | null)[];
  top: number;
  axis: [string, string, string];
  hover: (day: Day, i: number) => string;
  /** The panel the version labels sit above. */
  first: boolean;
}> = ({ agent, label, values, top, axis, hover, first }) => {
  const days = agent.latency_days;
  const count = days.length || 1;
  const index = Object.fromEntries(days.map((d, i) => [d.day, i]));
  const picked = new Set(agent.version_days ?? []);
  return (
    <div className="flex flex-col gap-2">
      <span className="text-label text-ink-secondary">{label}</span>
      <div className="relative h-32">
        <Axis value={axis[0]} className="top-0" />
        <Axis value={axis[1]} className="top-1/2" />
        <Axis value={axis[2]} className="bottom-0" />
        {agent.version && (agent.version_days ?? []).length > 0 && (
          <div
            className="pointer-events-none absolute top-0 right-0 bottom-0 left-10 grid gap-[2px]"
            style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
            aria-hidden
          >
            {days.map((d) => (
              <span key={d.day} className={cn(picked.has(d.day) && 'rounded bg-wash')} />
            ))}
          </div>
        )}
        <svg
          className="pointer-events-none absolute top-0 right-0 bottom-0 left-10 h-full w-[calc(100%-2.5rem)] overflow-visible text-ink"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden
        >
          <path
            d={linePath(values, top)}
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <div
          className="absolute top-0 right-0 bottom-0 left-10 grid"
          style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
        >
          {days.map((d, i) => {
            const v = values[i];
            return (
              <div key={d.day} className="relative" title={hover(d, i)}>
                {v != null && (
                  // A dot on each day with a value, so a single day still shows.
                  <span
                    className="absolute left-1/2 size-1.5 -translate-x-1/2 translate-y-1/2 rounded-full bg-ink"
                    style={{ bottom: `${(Math.min(v, top) / top) * 100}%` }}
                  />
                )}
              </div>
            );
          })}
        </div>
        <div className="pointer-events-none absolute top-0 right-0 bottom-0 left-10">
          {agent.version_marks.map((mark) => {
            const i = index[mark.day];
            if (i == null) return null;
            return (
              <div
                key={`${mark.day}-${mark.label}`}
                className="absolute top-0 bottom-0 border-l border-dashed border-ink-muted"
                style={{ left: `${((i + 0.5) / count) * 100}%` }}
              >
                {first && (
                  <span className="absolute -top-[22px] left-1.5 whitespace-nowrap text-label text-ink-secondary">
                    {mark.label}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

/** "Quality and latency": each day's score above each day's p50 latency, one day axis
 * and the version marks across both (designs/screens/Connexity Agent Profile.dc.html).
 * No goal lines until goals can be set. */
const QualityChart: FC<{ agent: AgentPagePublic }> = ({ agent }) => {
  const days = agent.latency_days;
  const count = days.length || 1;
  const top = Math.max(1, Math.ceil(agent.latency_peak ?? 0));
  const every = count > 31 ? 14 : 7;
  const scored = agent.score?.why_none?.includes('onboarding') !== true;
  return (
    <div className="flex flex-col gap-5 pt-5">
      {scored ? (
        <Panel
          agent={agent}
          label="Score"
          values={days.map((d) => d.score ?? null)}
          top={100}
          axis={['100', '50', '0']}
          hover={(d) =>
            d.score == null
              ? `${calendarDay(d.day)}: no checked calls`
              : `${calendarDay(d.day)}: score ${d.score} over ${d.checked_calls} checked ${d.checked_calls === 1 ? 'call' : 'calls'}`
          }
          first
        />
      ) : (
        <div className="flex flex-col gap-2">
          <span className="text-label text-ink-secondary">Score</span>
          <span className="text-label text-ink-muted">Ready when onboarding is complete</span>
        </div>
      )}
      <Panel
        agent={agent}
        label="Latency p50"
        values={days.map((d) => d.p50 ?? null)}
        top={top}
        axis={[`${top} s`, `${(top / 2).toFixed(top % 2 ? 1 : 0)} s`, '0']}
        hover={(d) =>
          d.p50 == null
            ? `${calendarDay(d.day)}: no replies`
            : `${calendarDay(d.day)}: p50 ${d.p50.toFixed(1)}s over ${d.replies} ${d.replies === 1 ? 'reply' : 'replies'}`
        }
        first={!scored}
      />
      <div
        className="ml-10 grid gap-[2px] text-label text-ink-muted"
        style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
      >
        {days.map((d, i) => (
          <span key={d.day} className="overflow-visible whitespace-nowrap">
            {i % every === 0 ? calendarDay(d.day) : ''}
          </span>
        ))}
      </div>
    </div>
  );
};

/** The agent's score for the period with its change, or why there is none, as the
 * Dashboard's Score tile reads it. Its base (checked calls) is on hover. */
const ScoreTile: FC<{ agent: AgentPagePublic }> = ({ agent }) => {
  const score = agent.score;
  const change = score?.change;
  return (
    <div
      title={
        score?.score != null
          ? `${score.checked_calls.toLocaleString()} checked calls in the period`
          : undefined
      }
      className="flex min-w-0 flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4"
    >
      <span className="text-label text-ink-secondary">Score</span>
      {score?.score != null ? (
        <span className="flex items-baseline gap-2">
          <span className="text-[30px] leading-9 font-medium">{score.score}</span>
          {change != null && (
            <span className="whitespace-nowrap text-label font-medium text-ink-secondary">
              {change > 0 ? '+' : change < 0 ? '−' : '±'}
              {Math.abs(change)}
            </span>
          )}
        </span>
      ) : (
        <span className="flex min-h-9 items-center text-label text-pretty text-ink-secondary">
          {!score || score.why_none?.includes('onboarding')
            ? 'Ready when onboarding is complete'
            : 'No checked calls yet'}
        </span>
      )}
    </div>
  );
};

const TILE = 'flex min-w-0 flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4';

/** The agent's critical issues; it opens them on the Issues page, on the picked version
 * when there is one. */
const CriticalTile: FC<{ agent: AgentPagePublic }> = ({ agent }) => {
  const count = agent.critical_issues ?? 0;
  return (
    <Link
      href={UrlGenerator.criticalIssues(agent.id, agent.period, agent.version)}
      className={cn(TILE, 'text-ink no-underline hover:bg-wash')}
    >
      <span
        className={cn(
          'flex items-center gap-1.5 text-label',
          count ? 'text-critical' : 'text-ink-secondary'
        )}
      >
        {count ? <OctagonAlert className="size-3.5" aria-hidden /> : null}
        Critical
      </span>
      <span
        className={cn('text-[30px] leading-9 font-medium', count ? 'text-critical' : undefined)}
      >
        {count.toLocaleString()}
      </span>
    </Link>
  );
};

const Overview: FC<{ agent: AgentPagePublic; onIssues: () => void }> = ({ agent, onIssues }) => (
  <div className="flex flex-col gap-6">
    {agent.version && agent.calls === 0 && (
      <p className="m-0 rounded-xl border border-hairline bg-surface-1 px-6 py-4 text-ink-secondary">
        No calls on version {agent.version} in the {PERIOD_LABELS[agent.period]?.toLowerCase()}.
      </p>
    )}
    <div className="grid auto-rows-fr grid-cols-2 gap-3 lg:grid-cols-5">
      <ScoreTile agent={agent} />
      <NumberTile
        label={agent.version ? `Calls on version ${agent.version}` : 'Calls'}
        value={agent.calls.toLocaleString()}
      />
      <div className="flex min-w-0 flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4">
        <span className="flex items-baseline gap-1.5 text-label text-ink-secondary">
          Latency <span className="text-ink-muted">p50/p95</span>
        </span>
        {agent.latency_p50 != null && agent.latency_p95 != null ? (
          <span className="flex items-baseline gap-0.5 whitespace-nowrap">
            <span className="text-[30px] leading-9 font-medium">
              {agent.latency_p50.toFixed(1)}
              <span className="text-title">s</span>
            </span>
            <span className="text-title leading-9 text-ink-secondary">
              /{agent.latency_p95.toFixed(1)}s
            </span>
          </span>
        ) : (
          <span className="flex min-h-9 items-center text-label text-ink-secondary">
            No replies timed yet
          </span>
        )}
      </div>
      <CriticalTile agent={agent} />
      <button
        type="button"
        onClick={onIssues}
        title="Open the Issues tab"
        className={cn(TILE, 'cursor-pointer text-left text-ink hover:bg-wash')}
      >
        <span className="text-label text-ink-secondary">Issues</span>
        <span className="text-[30px] leading-9 font-medium">
          {(agent.open_issues ?? 0).toLocaleString()}
        </span>
      </button>
    </div>
    <section className="flex flex-col gap-4 rounded-xl border border-hairline bg-surface-1 px-6 pt-5 pb-6">
      <h2 className="m-0 text-body font-medium">Details</h2>
      <div className="grid grid-cols-[160px_minmax(0,1fr)] items-baseline gap-x-4 gap-y-3">
        <Detail label="Platform">{agent.platform ? PLATFORMS[agent.platform] : '—'}</Detail>
        <Detail label="Agent type">{agent.type ? TYPES[agent.type] : '—'}</Detail>
        <Detail label="Live version">
          {agent.live_version
            ? `Version ${agent.live_version}${agent.live_since ? `, since ${dayLabel(agent.live_since)}` : ''}`
            : '—'}
        </Detail>
        <Detail label="Model">{agent.model ?? '—'}</Detail>
        <span className="text-label text-ink-secondary">Systems</span>
        <div className="flex flex-col gap-2">
          {(agent.systems ?? []).length === 0 && (
            <span className="text-ink-secondary">None used</span>
          )}
          {(agent.systems ?? []).map((system) => (
            <div key={system.name} className="flex flex-col">
              <span>
                {system.name}
                {system.version ? (
                  <span className="text-label text-ink-muted"> · version {system.version}</span>
                ) : null}
              </span>
              <span className="text-label text-ink-muted">{system.kind}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
    <section className="flex flex-col gap-4 rounded-xl border border-hairline bg-surface-1 px-6 pt-5 pb-6">
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h2 className="m-0 text-body font-medium">Quality and latency</h2>
          <span className="text-label text-ink-muted">
            {PERIOD_LABELS[agent.period]}
            {agent.version ? ` · version ${agent.version}` : ''} ·{' '}
            {(agent.score?.checked_calls ?? 0).toLocaleString()} checked{' '}
            {agent.score?.checked_calls === 1 ? 'call' : 'calls'} ·{' '}
            {agent.latency_replies.toLocaleString()}{' '}
            {agent.latency_replies === 1 ? 'reply' : 'replies'}
          </span>
        </div>
        {agent.version_marks.length > 0 && (
          <span className="flex items-center gap-1.5 text-label text-ink-secondary">
            <span className="h-3 border-l border-dashed border-ink-muted" />
            New version
          </span>
        )}
      </div>
      <QualityChart agent={agent} />
    </section>
  </div>
);

interface Props {
  agent: AgentPagePublic;
  tab: 'overview' | 'calls' | 'issues' | 'spec' | 'tests';
  /** The Issues tab's list, loaded on the server when it is open. */
  issues?: IssueListPublic | null;
  /** The agent's spec, loaded on the server; shown on the Spec tab and in its label. */
  spec?: SpecPublic | null;
  /** The Tests tab, loaded on the server; its coverage is in the tab's label. */
  tests?: TestsTabPublic | null;
  /** The Calls tab's list, loaded on the server. */
  children?: ReactNode;
}

/**
 * One agent (designs/screens/Connexity Agent Profile.dc.html): Overview, Calls, Issues,
 * Spec and Tests.
 */
export const AgentView: FC<Props> = ({ agent, tab, issues, spec, tests, children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();

  const go = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    const search = next.toString();
    startTransition(() => router.replace(search ? `${pathname}?${search}` : pathname));
  };

  const tabs = [
    { key: 'overview' as const, label: 'Overview', count: null },
    { key: 'calls' as const, label: 'Calls', count: agent.calls },
    { key: 'issues' as const, label: 'Issues', count: agent.open_issues ?? 0 },
    { key: 'spec' as const, label: 'Spec', count: spec?.spec?.rule_count ?? null },
    {
      key: 'tests' as const,
      label: 'Tests',
      count: null,
      suffix: tests?.coverage ? `${tests.coverage.pct}%` : null,
    },
  ];

  return (
    <div className={cn('flex max-w-[1120px] flex-col gap-6', pending && 'opacity-70')}>
      <div className="flex min-h-10 items-center justify-between gap-4">
        <div className="flex min-w-0 flex-wrap items-baseline gap-3">
          <Link
            href={UrlGenerator.agents()}
            title="Back to Agents"
            className="-ml-1.5 flex size-8 flex-none items-center justify-center self-center rounded-lg text-ink-secondary no-underline hover:bg-wash"
          >
            <ArrowLeft className="size-4" aria-hidden />
          </Link>
          <h1 className="m-0 text-title font-medium">{agent.name}</h1>
          {agent.spec === 'none' && (
            <span className="inline-flex h-5 flex-none items-center rounded-md border border-hairline px-1.5 text-label text-ink-muted">
              No spec
            </span>
          )}
          {caption(agent) && <span className="text-label text-ink-muted">{caption(agent)}</span>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {((agent.versions ?? []).length > 0 || agent.version) && (
            <Picker
              label="All versions"
              clearLabel="All versions"
              value={agent.version ?? undefined}
              options={[
                ...(agent.versions ?? []).map((v) => ({
                  value: v.version,
                  label: `Version ${v.version}${v.live ? ' · live' : ''}`,
                })),
                // A version from a link that has no calls still shows as picked.
                ...(agent.version &&
                !(agent.versions ?? []).some((v) => v.version === agent.version)
                  ? [{ value: agent.version, label: `Version ${agent.version}` }]
                  : []),
              ]}
              onPick={(value) => go({ version: value })}
              icon={<Layers className="size-4 text-ink-secondary" aria-hidden />}
              align="end"
            />
          )}
          <Picker
            label="Last 30 days"
            value={agent.period}
            options={Object.entries(PERIOD_LABELS).map(([value, label]) => ({ value, label }))}
            onPick={(value) => go({ period: value === '30d' ? undefined : value })}
            icon={<Calendar className="size-4 text-ink-secondary" aria-hidden />}
            align="end"
            clearable={false}
          />
        </div>
      </div>

      <div className="flex gap-6 border-b border-hairline" role="tablist">
        {tabs.map((item) => {
          const active = item.key === tab;
          return (
            <button
              key={item.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() =>
                go({ tab: item.key === 'overview' ? undefined : item.key, compare: undefined })
              }
              className={cn(
                '-mb-px flex h-10 items-center gap-1.5 border-0 border-b-2 bg-transparent px-0 text-body',
                active
                  ? 'border-ink font-medium text-ink'
                  : 'border-transparent text-ink-secondary hover:text-ink'
              )}
            >
              {item.label}
              {item.count != null && (
                <span className="text-label text-ink-muted">{item.count.toLocaleString()}</span>
              )}
              {'suffix' in item && item.suffix && (
                <span className="text-label font-normal text-ink-muted">{item.suffix}</span>
              )}
            </button>
          );
        })}
      </div>

      {tab === 'overview' && <Overview agent={agent} onIssues={() => go({ tab: 'issues' })} />}
      {tab === 'calls' && children}
      {tab === 'issues' && issues && <IssuesTab issues={issues} />}
      {tab === 'tests' && tests && (
        <TestsTab agentId={agent.id} version={agent.version} tests={tests} />
      )}
      {tab === 'spec' && spec && (
        <SpecTab
          spec={spec}
          liveSince={agent.live_since}
          onCompare={(version) => go({ compare: version })}
        />
      )}
    </div>
  );
};
