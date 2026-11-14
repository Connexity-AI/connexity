'use client';

import { useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { ArrowLeft, Calendar } from 'lucide-react';

import { NumberTile } from '@workspace/ui/components/number-tile';
import { cn } from '@workspace/ui/lib/utils';

import { PLATFORMS, seconds, TYPES } from '@/components/agents/agents-view';
import { parseTime } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';

import type { AgentPagePublic } from '@/client/types.gen';
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

/** Average latency per day, with a mark at each new version (design: "Quality and
 * latency", latency half only; no goal line until a goal can be set). */
const LatencyChart: FC<{ agent: AgentPagePublic }> = ({ agent }) => {
  const days = agent.latency_days;
  const count = days.length || 1;
  const top = Math.max(1, Math.ceil(agent.latency_peak ?? 0));
  const index = Object.fromEntries(days.map((d, i) => [d.day, i]));
  const every = count > 31 ? 14 : 7;
  return (
    <div className="flex flex-col gap-2 pt-5">
      <div className="relative h-40">
        <Axis value={`${top} s`} className="top-0" />
        <Axis value={`${(top / 2).toFixed(top % 2 ? 1 : 0)} s`} className="top-1/2" />
        <Axis value="0" className="bottom-0" />
        <div
          className="absolute top-0 right-0 bottom-0 left-10 grid items-end gap-[2px]"
          style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
        >
          {days.map((d) => (
            <div
              key={d.day}
              title={
                d.seconds == null
                  ? `${calendarDay(d.day)}: no calls`
                  : `${calendarDay(d.day)}: ${seconds(d.seconds)} over ${d.calls} ${d.calls === 1 ? 'call' : 'calls'}`
              }
              className="rounded-t-[2px] bg-ink-secondary"
              style={{
                height: d.seconds == null ? 0 : `${(d.seconds / top) * 100}%`,
                minHeight: d.seconds ? 2 : 0,
              }}
            />
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
    <div className="grid grid-cols-2 gap-3">
      <NumberTile label="Calls" value={agent.calls.toLocaleString()} />
      <NumberTile
        label="Latency"
        value={agent.latency_seconds == null ? '—' : agent.latency_seconds.toFixed(1)}
        unit={agent.latency_seconds == null ? undefined : 's'}
      />
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
          <h2 className="m-0 text-body font-medium">Latency</h2>
          <span className="text-label text-ink-muted">
            {PERIOD_LABELS[agent.period]} · {agent.latency_calls.toLocaleString()}{' '}
            {agent.latency_calls === 1 ? 'call' : 'calls'}
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
  tab: 'overview' | 'calls';
  /** The Calls tab's list, loaded on the server. */
  children?: ReactNode;
}

/**
 * One agent (designs/screens/Connexity Agent Profile.dc.html): Overview and Calls. The
 * Issues, Spec and Tests tabs, score and critical issues wait for their features (rule 14).
 */
export const AgentView: FC<Props> = ({ agent, tab, children }) => {
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

      <div className="flex gap-6 border-b border-hairline" role="tablist">
        {tabs.map((item) => {
          const active = item.key === tab;
          return (
            <button
              key={item.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => go({ tab: item.key === 'overview' ? undefined : item.key })}
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
            </button>
          );
        })}
      </div>

      {tab === 'overview' ? <Overview agent={agent} /> : children}
    </div>
  );
};
