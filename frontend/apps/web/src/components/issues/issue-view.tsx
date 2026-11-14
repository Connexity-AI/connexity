'use client';

import { useEffect, useRef, useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import {
  ArrowLeft,
  Check,
  ChevronRight,
  OctagonAlert,
  RotateCcw,
  TriangleAlert,
} from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { archiveIssueAction } from '@/actions/issues';
import { clock, parseTime, timeLabel } from '@/components/calls/format';
import { lastSeen } from '@/components/issues/issues-view';
import { isErrorApiResult } from '@/utils/api';

import type { IssueHistoryPublic, IssuePagePublic } from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2 Nov", in the viewer's time zone. */
const dayLabel = (iso: string) => {
  const date = parseTime(iso);
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
};

/** "2 Nov" for a UTC calendar day ("2026-11-02"). */
const calendarDay = (day: string) => {
  const [, month, date] = day.split('-').map(Number);
  return `${date} ${MONTHS[(month ?? 1) - 1]}`;
};

const DURATIONS = {
  until_spike: 'until it spikes',
  forever: 'forever',
} as const;

const Chip: FC<{ className: string; children: ReactNode }> = ({ className, children }) => (
  <span
    className={cn('inline-flex h-[22px] items-center gap-1 rounded-md px-2 text-label', className)}
  >
    {children}
  </span>
);

const StateChip: FC<{ issue: IssuePagePublic }> = ({ issue }) => {
  if (issue.state === 'reopened')
    return (
      <Chip className="bg-accent-ink font-medium text-on-accent">
        <RotateCcw className="size-3" aria-hidden />
        Reopened
      </Chip>
    );
  if (issue.state === 'resolved')
    return (
      <Chip className="bg-passed-bg font-medium text-passed">
        {issue.resolved_version ? `Resolved in version ${issue.resolved_version}` : 'Resolved'}
      </Chip>
    );
  if (issue.state === 'archived')
    return <Chip className="border border-hairline text-ink-secondary">Archived</Chip>;
  return <Chip className="border border-border-control text-ink">Open</Chip>;
};

const who = (by: string | null | undefined, assistant: string | null | undefined) =>
  assistant ? `your assistant, approved by ${by ?? 'a person'}` : by;

/** "by Alex, 9 Nov · until it spikes · 'reason'" */
const historyMeta = (line: IssueHistoryPublic) => {
  if (line.kind === 'spiked') return ` · ${line.reason ?? ''} · ${dayLabel(line.at)}`;
  const person =
    line.kind === 'opened' ? 'Connexity' : (who(line.by, line.assistant) ?? 'Connexity');
  const duration = line.duration ? ` · ${DURATIONS[line.duration]}` : '';
  const reason = line.reason ? ` · “${line.reason}”` : '';
  return ` by ${person}, ${dayLabel(line.at)}${duration}${reason}`;
};

const Tile: FC<{ label: string; value: ReactNode; unit?: string }> = ({ label, value, unit }) => (
  <div className="flex min-w-0 flex-1 flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4">
    <span className="text-label text-ink-secondary">{label}</span>
    <span className="flex items-baseline gap-1.5">
      <span className="whitespace-nowrap text-tile font-medium">{value}</span>
      {unit && <span className="text-body text-ink-muted">{unit}</span>}
    </span>
  </div>
);

const Card: FC<{ title: string; note?: ReactNode; children: ReactNode; flush?: boolean }> = ({
  title,
  note,
  children,
  flush,
}) => (
  <section
    className={cn(
      'rounded-xl border border-hairline bg-surface-1',
      flush ? 'overflow-hidden' : 'flex flex-col gap-4 px-6 pt-5 pb-6'
    )}
  >
    <div className={cn('flex items-baseline gap-3', flush && 'px-6 pt-5 pb-3')}>
      <h2 className="m-0 text-body font-medium">{title}</h2>
      {note}
    </div>
    {children}
  </section>
);

const ArchiveButton: FC<{ issueId: string }> = ({ issueId }) => {
  const router = useRouter();
  const box = useRef<HTMLDivElement>(null);
  const reasonField = useRef<HTMLTextAreaElement>(null);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [duration, setDuration] = useState<'until_spike' | 'forever'>('until_spike');
  const [failed, setFailed] = useState(false);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    if (!open) return;
    setTimeout(() => reasonField.current?.focus(), 30);
    const onDown = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const empty = !reason.trim();
  const confirm = () => {
    if (empty || pending) return;
    setFailed(false);
    startTransition(async () => {
      const result = await archiveIssueAction(issueId, reason.trim(), duration);
      if (isErrorApiResult(result)) {
        setFailed(true);
        return;
      }
      setOpen(false);
      setReason('');
      router.refresh();
    });
  };

  const options = [
    {
      value: 'until_spike' as const,
      label: 'Until it spikes',
      sub: 'Comes back if it starts happening twice as often as now.',
    },
    {
      value: 'forever' as const,
      label: 'Forever',
      sub: 'Stays archived until someone unarchives it.',
    },
  ];

  return (
    <div ref={box} className="relative flex-none">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border-control bg-transparent px-3 text-body text-ink hover:bg-wash"
      >
        Archive
      </button>
      {open && (
        <div className="absolute top-[42px] right-0 z-20 flex w-[380px] flex-col gap-3 rounded-xl border border-hairline bg-surface-2 p-4 shadow-[0_8px_24px_rgba(0,0,0,.18)]">
          <div className="flex flex-col gap-1">
            <span className="text-body font-medium">Archive this issue</span>
            <span className="text-label text-ink-secondary text-pretty">
              It leaves the open lists, Home and the roadmap, and is hidden on every call until it
              is unarchived. Its calls are still recorded.
            </span>
          </div>
          <textarea
            ref={reasonField}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={3}
            placeholder="Why it can be archived (required)"
            aria-label="Why it can be archived"
            className="w-full resize-y rounded-lg border border-border-control bg-surface-1 px-3 py-2 text-body text-ink outline-none"
          />
          <div className="flex flex-col gap-1.5" role="radiogroup" aria-label="How long">
            <span className="text-label text-ink-secondary">How long</span>
            {options.map((option) => {
              const on = duration === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => setDuration(option.value)}
                  className={cn(
                    'flex cursor-pointer items-start gap-2.5 rounded-lg border px-2.5 py-2 text-left text-body text-ink',
                    on ? 'border-border-control bg-wash' : 'border-transparent bg-transparent'
                  )}
                >
                  <span
                    className={cn(
                      'mt-[3px] size-4 flex-none rounded-full',
                      on ? 'border-[5px] border-ink' : 'border-[1.5px] border-border-control'
                    )}
                  />
                  <span className="flex flex-col">
                    <span>{option.label}</span>
                    <span className="text-label text-ink-muted text-pretty">{option.sub}</span>
                  </span>
                </button>
              );
            })}
          </div>
          {failed && (
            <span className="text-label text-critical">Could not archive it. Try again.</span>
          )}
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="h-9 rounded-lg border-0 bg-transparent px-3 text-body text-ink-secondary hover:bg-wash hover:text-ink"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={confirm}
              disabled={empty || pending}
              className={cn(
                'h-9 rounded-lg border-0 bg-accent-ink px-3.5 text-body font-medium text-on-accent',
                empty || pending ? 'cursor-default opacity-40' : 'cursor-pointer'
              )}
            >
              Archive
            </button>
          </div>
          <span className="text-label text-ink-muted text-pretty">
            Only a person can confirm this, here or through your assistant.
          </span>
        </div>
      )}
    </div>
  );
};

const Axis: FC<{ value: number; className: string }> = ({ value, className }) => (
  <div className={cn('absolute right-0 left-0 flex items-center gap-2', className)}>
    <span className="w-6 text-right text-label leading-none text-ink-muted">{value}</span>
    <span className="flex-1 border-t border-hairline" />
  </div>
);

const Chart: FC<{ issue: IssuePagePublic }> = ({ issue }) => {
  const yMax = Math.max(2, Math.ceil(issue.peak / 2) * 2);
  const index = Object.fromEntries(issue.days.map((d, i) => [d.day, i]));
  const count = issue.days.length || 30;
  const bar = issue.severity === 'critical' ? 'bg-critical' : 'bg-warning';
  return (
    <div className="flex flex-col gap-2 pt-5">
      <div className="relative h-40">
        <Axis value={yMax} className="top-0" />
        <Axis value={yMax / 2} className="top-1/2" />
        <Axis value={0} className="bottom-0" />
        <div
          className="absolute top-0 right-0 bottom-0 left-8 grid items-end gap-[3px]"
          style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
        >
          {issue.days.map((d) => (
            <div
              key={d.day}
              title={`${calendarDay(d.day)}: ${d.calls} ${d.calls === 1 ? 'call' : 'calls'}`}
              className={cn('rounded-t-[2px]', bar)}
              style={{ height: `${(d.calls / yMax) * 100}%`, minHeight: d.calls ? 2 : 0 }}
            />
          ))}
        </div>
        <div className="pointer-events-none absolute top-0 right-0 bottom-0 left-8">
          {issue.marks.map((mark) => {
            const i = index[mark.day];
            if (i == null) return null;
            return (
              <div
                key={`${mark.kind}-${mark.day}-${mark.label}`}
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
        className="ml-8 grid gap-[3px] text-label text-ink-muted"
        style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
      >
        {issue.days.map((d, i) => (
          <span key={d.day} className="overflow-visible whitespace-nowrap">
            {i % 7 === 0 ? calendarDay(d.day) : ''}
          </span>
        ))}
      </div>
    </div>
  );
};

const Step: FC<{ name: string; done: boolean; last: boolean; detail: ReactNode }> = ({
  name,
  done,
  last,
  detail,
}) => (
  <div className="flex min-w-0 flex-col gap-3">
    <div className="flex items-center">
      {done ? (
        <span className="flex size-5 flex-none items-center justify-center rounded-full bg-ink text-surface-1">
          <Check className="size-3" aria-hidden />
        </span>
      ) : (
        <span className="size-5 flex-none rounded-full border-[1.5px] border-border-control" />
      )}
      {!last && <span className="mx-2 h-0.5 flex-1 rounded-[1px] bg-hairline" />}
    </div>
    <div className="flex flex-col gap-0.5 pr-5">
      <span className={cn('text-body', done ? 'text-ink' : 'text-ink-secondary')}>{name}</span>
      {detail}
    </div>
  </div>
);

interface Props {
  issue: IssuePagePublic;
}

/**
 * One issue (designs/screens/Connexity Issue.dc.html). Left out until their features
 * exist (rule 14): the tip, incidents, the milestone, the agent link, and the chain's
 * spec, tests and confirmation steps.
 */
export const IssueView: FC<Props> = ({ issue }) => {
  const archived = issue.state === 'archived' ? issue.archive : null;
  const { found, fixed } = issue.chain;

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <div className="flex min-h-10 items-center justify-between gap-4">
        <div className="flex min-w-0 flex-wrap items-center gap-3">
          <Link
            href={UrlGenerator.issues()}
            title="Back to Issues"
            className="-ml-1.5 flex size-8 flex-none items-center justify-center rounded-lg text-ink-secondary no-underline hover:bg-wash"
          >
            <ArrowLeft className="size-4" aria-hidden />
          </Link>
          <h1 className="m-0 text-title font-medium">{issue.title}</h1>
          <span className="whitespace-nowrap text-label text-ink-secondary">
            {issue.agent_name}
          </span>
          {issue.severity === 'critical' ? (
            <Chip className="bg-critical-bg font-medium text-critical">
              <OctagonAlert className="size-3.5" aria-hidden />
              Critical
            </Chip>
          ) : (
            <Chip className="bg-warning-bg font-medium text-warning">
              <TriangleAlert className="size-3.5" aria-hidden />
              Warning
            </Chip>
          )}
          <StateChip issue={issue} />
        </div>
        {issue.state !== 'archived' && <ArchiveButton issueId={issue.id} />}
      </div>
      {archived && (
        <p className="-mt-3 ml-[30px] text-body text-ink-secondary text-pretty">
          Archived by {who(archived.by, archived.assistant)}, {dayLabel(archived.at)} ·{' '}
          {DURATIONS[archived.duration]}
          {archived.reason ? ` · “${archived.reason}”` : ''}
        </p>
      )}

      <div className="flex gap-3">
        <Tile
          label="Calls affected"
          value={issue.tiles.calls_affected.toLocaleString()}
          unit={`of ${issue.tiles.calls_total.toLocaleString()}`}
        />
        <Tile
          label="First seen"
          value={issue.tiles.first_seen_at ? dayLabel(issue.tiles.first_seen_at) : '—'}
        />
        <Tile label="Last seen" value={lastSeen(issue.tiles.last_seen_at)} />
      </div>

      <Card
        title="Progress"
        note={
          archived ? (
            <span className="ml-auto text-label text-ink-secondary">
              Stopped: archived on {dayLabel(archived.at)}
            </span>
          ) : undefined
        }
      >
        <div className="grid grid-cols-5">
          <Step
            name="Found"
            done={Boolean(found)}
            last={false}
            detail={
              found ? (
                <Link
                  href={UrlGenerator.call(found.call_id)}
                  className="text-label text-ink-secondary text-pretty"
                >
                  {dayLabel(found.at)}
                  {found.caller_last_four ? ` · call •••• ${found.caller_last_four}` : ''}
                </Link>
              ) : (
                <span className="text-label text-ink-muted">Not yet</span>
              )
            }
          />
          <Step
            name="Fixed in a version"
            done={Boolean(fixed)}
            last
            detail={
              <span className="text-label text-ink-muted text-pretty">
                {fixed
                  ? fixed.version
                    ? `Version ${fixed.version}`
                    : dayLabel(fixed.at)
                  : 'Not yet'}
              </span>
            }
          />
        </div>
      </Card>

      <Card
        title="Affected calls per day"
        note={<span className="text-label text-ink-muted">Last 30 days</span>}
      >
        <Chart issue={issue} />
      </Card>

      <Card
        title="Affected calls"
        note={<span className="text-label text-ink-muted">Latest first</span>}
        flush
      >
        <div className="grid h-10 grid-cols-[136px_96px_72px_104px_minmax(0,1fr)_16px] items-center gap-4 border-t border-hairline px-6 text-label text-ink-secondary">
          <span>Time</span>
          <span>Caller</span>
          <span className="text-right">Duration</span>
          <span>Result</span>
          <span>Moment</span>
          <span />
        </div>
        {issue.affected_calls.map((call) => (
          <Link
            key={call.call_id}
            href={UrlGenerator.call(call.call_id, call.moment.at_seconds)}
            title="Open the call at this moment"
            className="grid min-h-11 grid-cols-[136px_96px_72px_104px_minmax(0,1fr)_16px] items-center gap-4 border-t border-hairline px-6 text-body text-ink no-underline hover:bg-wash"
          >
            <span className="whitespace-nowrap">{timeLabel(call.started_at)}</span>
            <span className="whitespace-nowrap text-ink-secondary">
              {call.caller_last_four ? `•••• ${call.caller_last_four}` : '—'}
            </span>
            <span className="text-right text-ink-secondary">
              {call.duration_seconds != null ? clock(call.duration_seconds) : ''}
            </span>
            <span className="flex">
              {call.result === 'failed' && (
                <Chip className="bg-critical-bg font-medium text-critical">
                  <OctagonAlert className="size-3" aria-hidden />
                  Failed
                </Chip>
              )}
              {call.result === 'degraded' && (
                <Chip className="bg-warning-bg font-medium text-warning">
                  <TriangleAlert className="size-3" aria-hidden />
                  Degraded
                </Chip>
              )}
              {call.result === 'clean' && <span className="text-ink-secondary">Clean</span>}
              {call.result === 'unchecked' && <span className="text-ink-secondary">Unchecked</span>}
            </span>
            <span className="whitespace-nowrap text-ink-secondary">
              at {clock(call.moment.at_seconds)}
              {call.moment.times > 1 && (
                <span className="text-ink-muted"> · {call.moment.times} times</span>
              )}
            </span>
            <span className="flex text-ink-muted">
              <ChevronRight className="size-4" aria-hidden />
            </span>
          </Link>
        ))}
        {issue.affected_calls.length === 0 && (
          <div className="border-t border-hairline px-6 py-4 text-body text-ink-secondary">
            None in the last 30 days.
          </div>
        )}
        {issue.tiles.calls_affected > 0 && (
          <Link
            href={UrlGenerator.issueCalls(issue.id)}
            className="flex items-center gap-1.5 border-t border-hairline px-6 py-3.5 text-label text-ink-secondary no-underline hover:bg-wash hover:text-ink"
          >
            All {issue.tiles.calls_affected.toLocaleString()}{' '}
            {issue.tiles.calls_affected === 1 ? 'call' : 'calls'}
            <ChevronRight className="size-3.5" aria-hidden />
          </Link>
        )}
      </Card>

      <Card title="History" flush>
        {issue.history.map((line) => (
          <div
            key={`${line.kind}-${line.at}`}
            className="flex items-baseline justify-between gap-4 border-t border-hairline px-6 py-3"
          >
            <p className="m-0 text-pretty">
              <span>{line.what}</span>
              <span className="text-ink-secondary">{historyMeta(line)}</span>
            </p>
          </div>
        ))}
      </Card>
    </div>
  );
};
