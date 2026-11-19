'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import {
  Bot,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Hourglass,
  OctagonAlert,
  TriangleAlert,
} from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import type { DashboardArea, DashboardPublic } from '@/client/types.gen';
import type { FC, ReactNode, RefObject } from 'react';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const PERIODS = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
] as const;

/** "Nov 4" for a UTC calendar day ("2026-11-04"). */
const dayLabel = (day: string) => {
  const [, month, date] = day.split('-').map(Number);
  return `${MONTHS[(month ?? 1) - 1]} ${date}`;
};

const count = (n: number) => n.toLocaleString('en-US');

const share = (value: number | null | undefined) => {
  if (value == null || value === 0) return '0%';
  const percent = value * 100;
  return percent < 1 ? '<1%' : `${Math.round(percent)}%`;
};

const useOutside = (ref: RefObject<HTMLElement | null>, close: () => void) => {
  useEffect(() => {
    const onDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) close();
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [ref, close]);
};

const Picker: FC<{
  icon: ReactNode;
  label: string;
  options: { value: string; label: string }[];
  current: string;
  onPick: (value: string) => void;
  grow?: boolean;
}> = ({ icon, label, options, current, onPick, grow }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useOutside(ref, () => setOpen(false));
  return (
    <div ref={ref} className={cn('relative', grow ? 'min-w-0 flex-auto' : 'flex-none')}>
      <button
        type="button"
        aria-haspopup="listbox"
        onClick={() => setOpen((value) => !value)}
        className="flex h-9 w-full items-center gap-2 whitespace-nowrap rounded-lg border border-border-control bg-transparent px-3 text-body text-ink hover:bg-wash"
      >
        <span className="flex-none text-ink-secondary">{icon}</span>
        <span className="min-w-0 flex-1 truncate text-left">{label}</span>
        <ChevronDown className="size-4 flex-none text-ink-secondary" aria-hidden />
      </button>
      {open && (
        <div
          role="listbox"
          className="absolute top-[42px] right-0 z-20 min-w-[220px] rounded-lg border border-hairline bg-surface-2 p-1 shadow-[0_8px_24px_rgba(0,0,0,.18)]"
        >
          {options.map((option) => (
            <div
              key={option.value}
              role="option"
              aria-selected={option.value === current}
              onClick={() => {
                setOpen(false);
                onPick(option.value);
              }}
              className="flex h-9 cursor-pointer items-center justify-between gap-3 whitespace-nowrap rounded-md px-3 text-body hover:bg-wash"
            >
              <span>{option.label}</span>
              {option.value === current && <Check className="size-4" aria-hidden />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const Tile: FC<{ children: ReactNode }> = ({ children }) => (
  <div className="flex flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4">
    {children}
  </div>
);

const Strip: FC<{ onboarding: NonNullable<DashboardPublic['onboarding']> }> = ({ onboarding }) => {
  const next = onboarding.steps.find((step) => !step.done)?.key;
  return (
    <div
      role="status"
      className="flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-1.5 rounded-lg border border-hairline px-4 py-2 text-label text-ink-secondary"
    >
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
        {onboarding.steps.map((step, index) => (
          <span key={step.key} className="flex items-center gap-2.5">
            {index > 0 && <span className="text-ink-muted">·</span>}
            <span
              className={cn(
                'inline-flex items-center gap-1',
                step.key === next && 'font-medium text-ink',
                !step.done && step.key !== next && 'text-ink-muted'
              )}
            >
              {step.done && <Check className="size-3.5" aria-hidden />}
              {step.label}
            </span>
          </span>
        ))}
      </div>
      <span>
        {onboarding.areas_checked} of {onboarding.areas_total} areas checked
      </span>
    </div>
  );
};

const Chart: FC<{ dashboard: DashboardPublic }> = ({ dashboard }) => {
  const days = dashboard.days;
  const n = days.length || 1;
  const peak = Math.max(1, ...days.map((d) => d.calls));
  const step = peak > 40 ? 20 : peak > 20 ? 10 : 4;
  const max = Math.ceil(peak / step) * step;
  const every = n <= 8 ? 1 : n <= 31 ? 7 : 14;
  const index = new Map(days.map((d, i) => [d.day, i]));
  const marks = dashboard.marks
    .map((mark) => ({ ...mark, i: index.get(mark.day) }))
    .filter((mark): mark is typeof mark & { i: number } => mark.i !== undefined);
  const gap = n > 60 ? 1 : n > 14 ? 3 : 8;
  return (
    <div className="flex min-w-0 flex-col gap-4 rounded-xl border border-hairline bg-surface-1 p-6">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <h2 className="m-0 text-body font-medium">Calls per day</h2>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-label text-ink-secondary">
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-[2px] bg-border-control" />
            Calls
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-[2px] bg-warning" />
            Degraded
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-[2px] bg-critical" />
            Failed
          </span>
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <div className="relative h-[180px]">
          {[max, max / 2, 0].map((value, i) => (
            <div
              key={i}
              className="absolute right-0 left-0 flex items-center gap-2"
              style={{ top: `${i * 50}%` }}
            >
              <span className="w-6 text-right text-label leading-none text-ink-muted">{value}</span>
              <span className="flex-1 border-t border-hairline" />
            </div>
          ))}
          <div
            className="absolute top-0 right-0 bottom-0 left-8 grid items-end"
            style={{ gridTemplateColumns: `repeat(${n},minmax(0,1fr))`, gap }}
          >
            {days.map((d) => (
              <div
                key={d.day}
                title={`${dayLabel(d.day)}: ${d.calls} calls, ${d.failed} failed, ${d.degraded} degraded`}
                className="flex flex-col overflow-hidden rounded-t-[2px]"
                style={{ height: `${(d.calls / max) * 100}%` }}
              >
                <div className="bg-critical" style={{ flex: `${d.failed} 0 0` }} />
                <div className="bg-warning" style={{ flex: `${d.degraded} 0 0` }} />
                <div
                  className="bg-border-control"
                  style={{ flex: `${d.calls - d.failed - d.degraded} 0 0` }}
                />
              </div>
            ))}
          </div>
          <div className="pointer-events-none absolute top-0 right-0 bottom-0 left-8">
            {marks.map((mark) => (
              <div
                key={`${mark.agent_name}-${mark.version}`}
                className="absolute top-0 bottom-0 border-l border-dashed border-ink-muted opacity-70"
                style={{ left: `${((mark.i + 0.5) / n) * 100}%` }}
              />
            ))}
          </div>
        </div>
        <div className="relative ml-8 h-[18px]">
          {marks.map((mark) => (
            <span
              key={`${mark.agent_name}-${mark.version}`}
              title={`${mark.agent_name} moved to ${mark.version} on ${dayLabel(mark.day)}`}
              className="absolute top-0 -translate-x-1/2 cursor-default whitespace-nowrap font-mono text-label font-medium text-ink"
              style={{ left: `${((mark.i + 0.5) / n) * 100}%` }}
            >
              {mark.version}
            </span>
          ))}
        </div>
        <div className="relative ml-8 h-[18px] text-label text-ink-muted">
          {days.map((d, i) =>
            i % every === 0 ? (
              <span
                key={d.day}
                className="absolute whitespace-nowrap"
                style={{ left: `${(i / n) * 100}%` }}
              >
                {dayLabel(d.day)}
              </span>
            ) : null
          )}
        </div>
        <div className="ml-8 text-center text-label text-ink-muted">Day</div>
      </div>
    </div>
  );
};

const STATUS = {
  critical: {
    word: 'Critical',
    icon: OctagonAlert,
    chip: 'bg-critical-bg text-critical',
  },
  warning: {
    word: 'Warning',
    icon: TriangleAlert,
    chip: 'bg-warning-bg text-warning',
  },
  healthy: {
    word: 'Healthy',
    icon: CheckCircle2,
    chip: 'bg-passed-bg text-passed',
  },
  not_checked: {
    word: 'Not checked yet',
    icon: Hourglass,
    chip: 'bg-unchecked-bg text-ink-secondary',
  },
} as const;

const areaLine = (area: DashboardArea) => {
  if (area.status === 'healthy') return 'No issues';
  if (area.status === 'not_checked') return area.waits_for ?? '';
  return area.top_issue_title ?? '';
};

const AreaRow: FC<{
  area: DashboardArea;
  first: boolean;
  period: string;
  agent: string | null | undefined;
}> = ({ area, first, period, agent }) => {
  const status = STATUS[area.status];
  const Icon = status.icon;
  const links = area.status === 'critical' || area.status === 'warning';
  const line = areaLine(area);
  const body = (
    <>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="text-pretty text-ink">{area.name}</span>
        <span className="text-label text-pretty text-ink-secondary md:hidden">{line}</span>
      </span>
      <span className="flex min-w-0">
        <span
          className={cn(
            'inline-flex h-[22px] items-center gap-1 whitespace-nowrap rounded-md px-2 text-label font-medium',
            status.chip
          )}
        >
          <Icon className="size-3.5 flex-none" aria-hidden />
          {status.word}
        </span>
      </span>
      <span className="text-right text-ink">{links ? share(area.share) : ''}</span>
      <span
        className={cn(
          'hidden min-w-0 truncate md:block',
          area.status === 'healthy' ? 'text-ink-muted' : 'text-ink-secondary'
        )}
      >
        {line}
      </span>
      <span className="hidden text-ink-muted md:flex">
        {links && <ChevronRight className="size-4" aria-hidden />}
      </span>
    </>
  );
  const className = cn(
    'grid min-h-[52px] items-start gap-3 px-4 py-3 text-body text-ink no-underline sm:px-6',
    'grid-cols-[minmax(0,1fr)_auto_40px]',
    'md:grid-cols-[minmax(0,1.2fr)_160px_56px_minmax(0,2fr)_16px] md:items-center md:gap-4 md:py-0',
    'border-t border-hairline',
    // Under the column header on wide screens the first row needs no line of its own.
    first && 'md:border-t-0'
  );
  return links ? (
    <Link href={UrlGenerator.issuesInArea(area.key, { period, agent })} className={cn(className, 'hover:bg-wash')}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  );
};

/** The Dashboard. Every number comes from the backend; nothing here is sample data. */
export const DashboardView: FC<{ dashboard: DashboardPublic }> = ({ dashboard }) => {
  const router = useRouter();
  const go = (changes: { period?: string; agent?: string | null }) =>
    router.push(
      UrlGenerator.dashboard({
        period: changes.period ?? dashboard.period,
        agent:
          changes.agent === null ? undefined : (changes.agent ?? dashboard.agent_id ?? undefined),
      })
    );
  const agentLabel =
    dashboard.agents.find((agent) => agent.value === dashboard.agent_id)?.label ?? 'All agents';
  const score = dashboard.score;
  const change = score.change;
  const latency = dashboard.latency;

  return (
    <main className="min-w-0 flex-1 px-4 pt-4 pb-10 sm:px-8 sm:pt-6 sm:pb-12">
      <div className="flex max-w-[1120px] flex-col gap-6">
        <div className="flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-3">
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="m-0 text-title font-medium">Dashboard</h1>
            <span className="text-body text-ink-secondary">
              {dashboard.agents_counted} {dashboard.agents_counted === 1 ? 'agent' : 'agents'} ·{' '}
              {count(dashboard.calls)} calls
            </span>
          </div>
          <div className="flex w-full items-center gap-2 sm:w-auto">
            <Picker
              grow
              icon={<Bot className="size-4" />}
              label={agentLabel}
              current={dashboard.agent_id ?? 'all'}
              options={[
                { value: 'all', label: 'All agents' },
                ...dashboard.agents.map((agent) => ({ value: agent.value, label: agent.label })),
              ]}
              onPick={(value) => go({ agent: value === 'all' ? null : value })}
            />
            <Picker
              icon={<Calendar className="size-4" />}
              label={PERIODS.find((p) => p.value === dashboard.period)?.label ?? 'Last 30 days'}
              current={dashboard.period}
              options={PERIODS.map((p) => ({ value: p.value, label: p.label }))}
              onPick={(value) => go({ period: value })}
            />
          </div>
        </div>

        {dashboard.onboarding && <Strip onboarding={dashboard.onboarding} />}

        <div className="grid auto-rows-fr grid-cols-2 gap-3 lg:grid-cols-4">
          <Tile>
            <span className="text-label text-ink-secondary">Score</span>
            {score.score != null ? (
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
                {dashboard.onboarding || score.why_none?.includes('onboarding')
                  ? 'Ready when onboarding is complete'
                  : 'No checked calls yet'}
              </span>
            )}
          </Tile>
          <Tile>
            <span className="flex items-center gap-1.5 text-label text-critical">
              <OctagonAlert className="size-3.5" aria-hidden />
              Failed
            </span>
            <span className="flex items-baseline gap-2">
              <span className="text-[30px] leading-9 font-medium text-critical">
                {count(dashboard.failed)}
              </span>
              <span className="text-label text-ink-secondary">{share(dashboard.failed_share)}</span>
            </span>
          </Tile>
          <Tile>
            <span className="flex items-center gap-1.5 text-label text-warning">
              <TriangleAlert className="size-3.5" aria-hidden />
              Degraded
            </span>
            <span className="flex items-baseline gap-2">
              <span className="text-[30px] leading-9 font-medium text-warning">
                {count(dashboard.degraded)}
              </span>
              <span className="text-label text-ink-secondary">
                {share(dashboard.degraded_share)}
              </span>
            </span>
          </Tile>
          <Tile>
            <span className="flex items-baseline gap-1.5 text-label text-ink-secondary">
              Latency <span className="text-ink-muted">p50/p95</span>
            </span>
            {latency.p95 != null && latency.p50 != null ? (
              <span className="flex items-baseline gap-0.5">
                <span className="flex-none whitespace-nowrap text-[30px] leading-9 font-medium">
                  {latency.p50.toFixed(1)}
                  <span className="text-title">s</span>
                </span>
                <span className="flex-none whitespace-nowrap text-title leading-9 text-ink-secondary">
                  /{latency.p95.toFixed(1)}s
                </span>
              </span>
            ) : (
              <span className="flex min-h-9 items-center text-label text-ink-secondary">
                No answers timed yet
              </span>
            )}
          </Tile>
        </div>

        <Chart dashboard={dashboard} />

        <section className="min-w-0 overflow-hidden rounded-xl border border-hairline bg-surface-1">
          <div className="px-6 pt-5 pb-3">
            <h2 className="m-0 text-body font-medium">Areas</h2>
          </div>
          <div className="hidden h-10 grid-cols-[minmax(0,1.2fr)_160px_56px_minmax(0,2fr)_16px] items-center gap-4 border-b border-hairline px-6 text-label text-ink-secondary md:grid">
            <span>Area</span>
            <span>Status</span>
            <span className="text-right">Calls</span>
            <span>Issue</span>
            <span />
          </div>
          {dashboard.areas.map((area, index) => (
            <AreaRow
              key={area.key}
              area={area}
              first={index === 0}
              period={dashboard.period}
              agent={dashboard.agent_id}
            />
          ))}
        </section>
      </div>
    </main>
  );
};
