'use client';

import { useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { ArrowLeft, Calendar, Layers } from 'lucide-react';

import { NumberTile } from '@workspace/ui/components/number-tile';
import { cn } from '@workspace/ui/lib/utils';

import { PLATFORMS, TYPES } from '@/components/agents/agents-view';
import { SpecTab } from '@/components/agents/spec-tab';
import { TestsTab } from '@/components/agents/tests-tab';
import { parseTime } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';

import type { AgentPagePublic, SpecPublic, TestsTabPublic } from '@/client/types.gen';
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

/** The line through the p50 of each day that had replies, in a 0..100 box; days without
 * replies are stepped over, so calls a few days apart still draw a line. */
const linePath = (days: AgentPagePublic['latency_days'], top: number) =>
  days
    .map((d, i) =>
      d.p50 == null
        ? null
        : `${(((i + 0.5) / (days.length || 1)) * 100).toFixed(2)} ${(100 - (Math.min(d.p50, top) / top) * 100).toFixed(2)}`
    )
    .filter((point): point is string => point != null)
    .map((point, i) => `${i ? 'L' : 'M'}${point}`)
    .join(' ');

/** Each day's p50 latency as one line, with a mark at each new version (design item 34:
 * "Latency p50"; no goal line until a goal can be set). */
const LatencyChart: FC<{ agent: AgentPagePublic }> = ({ agent }) => {
  const days = agent.latency_days;
  const count = days.length || 1;
  const top = Math.max(1, Math.ceil(agent.latency_peak ?? 0));
  const index = Object.fromEntries(days.map((d, i) => [d.day, i]));
  const every = count > 31 ? 14 : 7;
  // With a version picked, the days it ran are shaded.
  const picked = new Set(agent.version_days ?? []);
  return (
    <div className="flex flex-col gap-2 pt-5">
      <div className="relative h-40">
        <Axis value={`${top} s`} className="top-0" />
        <Axis value={`${(top / 2).toFixed(top % 2 ? 1 : 0)} s`} className="top-1/2" />
        <Axis value="0" className="bottom-0" />
        {agent.version && (agent.version_days ?? []).length > 0 && (
          <div
            className="pointer-events-none absolute top-0 right-0 bottom-0 left-10 grid gap-[2px]"
            style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
            aria-hidden
          >
            {days.map((d) => (
              <span
                key={d.day}
                className={cn(picked.has(d.day) && 'rounded bg-wash')}
              />
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
            d={linePath(days, top)}
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
          {days.map((d) => (
            <div
              key={d.day}
              className="relative"
              title={
                d.p50 == null
                  ? `${calendarDay(d.day)}: no replies`
                  : `${calendarDay(d.day)}: p50 ${d.p50.toFixed(1)}s over ${d.replies} ${d.replies === 1 ? 'reply' : 'replies'}`
              }
            >
              {d.p50 != null && (
                // A dot on each day with replies, so a single day still shows.
                <span
                  className="absolute left-1/2 size-1.5 -translate-x-1/2 translate-y-1/2 rounded-full bg-ink"
                  style={{ bottom: `${(Math.min(d.p50, top) / top) * 100}%` }}
                />
              )}
            </div>
          ))}
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
                <span className="absolute -top-[22px] left-1.5 whitespace-nowrap text-label text-ink-secondary">
                  {mark.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
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

const Overview: FC<{ agent: AgentPagePublic }> = ({ agent }) => (
  <div className="flex flex-col gap-6">
    {agent.version && agent.calls === 0 && (
      <p className="m-0 rounded-xl border border-hairline bg-surface-1 px-6 py-4 text-ink-secondary">
        No calls on version {agent.version} in the {PERIOD_LABELS[agent.period]?.toLowerCase()}.
      </p>
    )}
    <div className="grid grid-cols-2 gap-3">
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
          <h2 className="m-0 text-body font-medium">Latency p50</h2>
          <span className="text-label text-ink-muted">
            {PERIOD_LABELS[agent.period]}
            {agent.version ? ` · version ${agent.version}` : ''} ·{' '}
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
      <LatencyChart agent={agent} />
    </section>
  </div>
);

interface Props {
  agent: AgentPagePublic;
  tab: 'overview' | 'calls' | 'spec' | 'tests';
  /** The agent's spec, loaded on the server; shown on the Spec tab and in its label. */
  spec?: SpecPublic | null;
  /** The Tests tab, loaded on the server; its coverage is in the tab's label. */
  tests?: TestsTabPublic | null;
  /** The Calls tab's list, loaded on the server. */
  children?: ReactNode;
}

/**
 * One agent (designs/screens/Connexity Agent Profile.dc.html): Overview, Calls, Spec and
 * Tests. The Issues tab, score and critical issues wait for their features (rule 14).
 */
export const AgentView: FC<Props> = ({ agent, tab, spec, tests, children }) => {
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
                ...(agent.version && !(agent.versions ?? []).some((v) => v.version === agent.version)
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

      {tab === 'overview' && <Overview agent={agent} />}
      {tab === 'calls' && children}
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
