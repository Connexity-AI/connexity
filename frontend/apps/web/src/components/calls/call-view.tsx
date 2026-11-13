'use client';

import {
  ArrowLeft,
  ChevronRight,
  CircleCheck,
  OctagonAlert,
  Pause,
  Play,
  TriangleAlert,
  Wrench,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';

import { cn } from '@workspace/ui/lib/utils';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { clock, shortDuration, timeLabel } from '@/components/calls/format';

import type {
  CallScreenEntry,
  CallScreenFinding,
  CallScreenPublic,
  KeyValue,
} from '@/client/types.gen';
import type { CSSProperties, FC } from 'react';

const CLAMP = 180;

const foundBy = (finding: CallScreenFinding) =>
  finding.found_by === 'model' ? 'Found by a model' : 'Found by a rule';

const ResultLabel: FC<{ result: CallScreenPublic['result'] }> = ({ result }) => {
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
  return (
    <span className="inline-flex h-[22px] items-center rounded-md border border-hairline px-2 text-label text-ink-secondary">
      {result === 'clean' ? 'Clean' : 'Unchecked'}
    </span>
  );
};

const FindingChip: FC<{ finding: CallScreenFinding }> = ({ finding }) =>
  finding.severity === 'critical' ? (
    <span className="inline-flex min-h-6 items-center gap-1.5 rounded-md bg-critical-bg px-2 py-0.5 text-label text-critical">
      <OctagonAlert className="size-3.5 flex-none" aria-hidden />
      <span>
        <span className="font-medium">{finding.text}</span> · {finding.category} · {foundBy(finding)}
      </span>
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 text-label text-warning">
      <TriangleAlert className="size-3.5 flex-none" aria-hidden />
      <span>
        {finding.text}{' '}
        <span className="text-ink-muted">
          · {finding.category} · {foundBy(finding)}
        </span>
      </span>
    </span>
  );

const Values: FC<{ title: string; values: KeyValue[]; id: string }> = ({ title, values, id }) => {
  const [full, setFull] = useState<Record<string, boolean>>({});
  if (values.length === 0) return null;
  return (
    <div className="flex flex-col gap-1">
      <span className="text-label text-ink-muted">{title}</span>
      {values.map((kv) => {
        const key = `${id}-${kv.key}`;
        const clamped = kv.value.length > CLAMP && !full[key];
        return (
          <div
            key={kv.key}
            className="grid grid-cols-[160px_minmax(0,1fr)] gap-4 font-mono text-label leading-5"
          >
            <span className="break-all text-ink-muted">{kv.key}</span>
            <div className="flex min-w-0 flex-col items-start">
              <span className={cn('whitespace-pre-wrap break-all text-ink', clamped && 'line-clamp-3')}>
                {kv.value}
              </span>
              {clamped && (
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    setFull((f) => ({ ...f, [key]: true }));
                  }}
                  className="border-0 bg-transparent p-0 font-sans text-label text-ink-secondary underline"
                >
                  Show all
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const toolLine = (entry: CallScreenEntry) =>
  [entry.tool, entry.status, entry.duration_ms != null ? shortDuration(entry.duration_ms) : null]
    .filter(Boolean)
    .join(' · ');

interface Props {
  call: CallScreenPublic;
  recordingUrl: string | null;
}

/** A single call (designs/screens/Connexity Call.dc.html). Read only. */
export const CallView: FC<Props> = ({ call, recordingUrl }) => {
  const audio = useRef<HTMLAudioElement>(null);
  const transcript = useRef<HTMLDivElement>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [audioFailed, setAudioFailed] = useState(false);
  const [open, setOpen] = useState<Record<number, boolean>>({});
  const follow = useRef(false);

  const hasAudio = Boolean(recordingUrl) && !audioFailed;
  const lastEnd = call.entries.reduce((max, e) => Math.max(max, e.end_seconds ?? e.at_seconds), 0);
  const duration = Math.max(call.duration_seconds ?? 0, lastEnd, 1);
  const findingsById = useMemo(
    () => Object.fromEntries(call.findings.map((f) => [f.id, f])),
    [call.findings]
  );

  const activeIndex = useMemo(() => {
    let index = 0;
    call.entries.forEach((entry, i) => {
      if (entry.at_seconds <= t + 0.05) index = i;
    });
    return index;
  }, [call.entries, t]);

  const scrollTo = (index: number, always: boolean) => {
    const pane = transcript.current;
    const row = pane?.querySelector<HTMLElement>(`[data-entry="${index}"]`);
    if (!pane || !row) return;
    const top = row.offsetTop;
    const bottom = top + row.offsetHeight;
    if (always || top < pane.scrollTop || bottom > pane.scrollTop + pane.clientHeight)
      pane.scrollTop = Math.max(0, top - 48);
  };

  const seek = (seconds: number) => {
    const at = Math.min(Math.max(seconds, 0), duration);
    setT(at);
    follow.current = true;
    if (audio.current && hasAudio) audio.current.currentTime = at;
  };

  // Open at the critical moment, when there is one.
  useEffect(() => {
    const critical = call.findings.find((f) => f.severity === 'critical');
    if (critical) {
      setT(critical.at_seconds);
      if (critical.entry_index != null) {
        const index = critical.entry_index;
        setTimeout(() => scrollTo(index, true), 60);
      }
    }
    // Once, on open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (playing || follow.current) {
      scrollTo(activeIndex, false);
      follow.current = false;
    }
  }, [activeIndex, playing]);

  const togglePlay = () => {
    const player = audio.current;
    if (!player) return;
    if (player.paused) {
      if (Math.abs(player.currentTime - t) > 0.5) player.currentTime = t;
      void player.play().catch(() => setAudioFailed(true));
    } else {
      player.pause();
    }
  };

  const pct = (seconds: number) => `${(Math.min(seconds, duration) / duration) * 100}%`;
  const bars = (speaker: 'agent' | 'caller') =>
    call.entries
      .filter((e) => e.kind === 'turn' && e.speaker === speaker)
      .map((e, i) => {
        const end = e.end_seconds ?? e.at_seconds + 1;
        const style: CSSProperties = {
          left: pct(e.at_seconds),
          width: `${Math.max(0.25, ((end - e.at_seconds) / duration) * 100)}%`,
        };
        return <div key={i} className="absolute inset-y-0 rounded bg-ink" style={style} />;
      });

  const dm = call.duration_seconds ?? Math.round(lastEnd);
  const meta = [
    timeLabel(call.started_at),
    `${Math.floor(dm / 60)} min ${dm % 60} s`,
    call.caller_last_four ? `•••• ${call.caller_last_four}` : null,
    call.version ? `Version ${call.version}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="flex max-w-[1120px] min-w-[880px] flex-col gap-6">
      <div className="flex min-h-10 flex-wrap items-center gap-3">
        <Link
          href={UrlGenerator.calls()}
          title="Back to Calls"
          className="-ml-1.5 flex size-8 flex-none items-center justify-center rounded-lg text-ink-secondary no-underline hover:bg-wash"
        >
          <ArrowLeft className="size-4" aria-hidden />
        </Link>
        <h1 className="m-0 text-title font-medium text-ink">{call.agent_name}</h1>
        <span className="whitespace-nowrap text-label text-ink-muted">{meta}</span>
        <ResultLabel result={call.result} />
      </div>

      <section className="flex items-start gap-4 rounded-xl border border-hairline bg-surface-1 px-6 pt-5 pb-4">
        {hasAudio ? (
          <div className="mt-[19px] flex h-10 flex-none items-center gap-4">
            <button
              type="button"
              onClick={togglePlay}
              title={playing ? 'Pause' : 'Play'}
              className="flex size-10 flex-none items-center justify-center rounded-full border-0 bg-ink text-on-accent hover:opacity-90"
            >
              {playing ? <Pause className="size-4" aria-hidden /> : <Play className="size-4" aria-hidden />}
            </button>
            <span className="w-10 flex-none text-label text-ink">{clock(t)}</span>
            <audio
              ref={audio}
              src={recordingUrl ?? undefined}
              preload="metadata"
              onTimeUpdate={(event) => setT(event.currentTarget.currentTime)}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
              onError={() => setAudioFailed(true)}
            />
          </div>
        ) : (
          <span className="mt-[19px] flex h-10 flex-none items-center whitespace-nowrap text-label text-ink-muted">
            Recording unavailable
          </span>
        )}
        <div className="mt-2.5 grid min-w-0 flex-1 grid-cols-[44px_minmax(0,1fr)] grid-rows-[52px_18px] gap-x-3 gap-y-1.5">
          <div className="relative text-label leading-4 text-ink-muted">
            <span className="absolute top-2.5 left-0">Agent</span>
            <span className="absolute top-8 left-0">Caller</span>
          </div>
          <div
            className="relative cursor-pointer"
            title="Seek"
            onClick={(event) => {
              const rect = event.currentTarget.getBoundingClientRect();
              seek(((event.clientX - rect.left) / rect.width) * duration);
            }}
          >
            <div className="absolute inset-x-0 top-3.5 h-2 overflow-hidden rounded bg-unchecked-bg">
              <div className="absolute inset-0 opacity-[.32]">{bars('agent')}</div>
            </div>
            <div className="absolute inset-x-0 top-9 h-2 overflow-hidden rounded bg-unchecked-bg">
              <div className="absolute inset-0 opacity-20">{bars('caller')}</div>
            </div>
            {call.entries.map((entry, i) =>
              entry.kind === 'tool' ? (
                <button
                  key={`tick-${i}`}
                  type="button"
                  title={`${clock(entry.at_seconds)} · ${toolLine(entry)}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    seek(entry.at_seconds);
                  }}
                  className="absolute top-[23px] z-[1] h-3 w-3 border-0 bg-transparent p-0"
                  style={{ left: `calc(${pct(entry.at_seconds)} - 6px)` }}
                >
                  <span className="absolute top-0.5 left-[5px] h-2 w-0.5 rounded-[1px] bg-ink-muted" />
                </button>
              ) : null
            )}
            {call.findings.map((finding) => (
              <button
                key={`mark-${finding.id}`}
                type="button"
                title={`${clock(finding.at_seconds)} · ${finding.text}`}
                onClick={(event) => {
                  event.stopPropagation();
                  seek(finding.at_seconds);
                }}
                className={cn(
                  'absolute top-0 h-3 w-4 border-0 bg-transparent p-0',
                  finding.severity === 'critical' ? 'z-[3]' : 'z-[2]'
                )}
                style={{ left: `calc(${pct(finding.at_seconds)} - 8px)` }}
              >
                {finding.severity === 'critical' ? (
                  <>
                    <span className="absolute top-2 left-[7px] h-10 w-0.5 rounded-[1px] bg-critical" />
                    <OctagonAlert className="absolute -top-2.5 left-0 size-4 text-critical" aria-hidden />
                  </>
                ) : (
                  <span className="absolute top-0.5 left-[7px] h-2 w-0.5 rounded-[1px] bg-warning" />
                )}
              </button>
            ))}
            <div
              className="pointer-events-none absolute top-2.5 -ml-px h-[38px] w-0.5 rounded-[1px] bg-ink"
              style={{ left: pct(t) }}
            />
          </div>
          <span />
          <div className="flex justify-between text-label text-ink-muted">
            <span>0:00</span>
            <span>{clock(duration)}</span>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
        <div className="flex items-baseline gap-3 px-6 pt-5 pb-3">
          <h2 className="m-0 text-body font-medium text-ink">Findings</h2>
          {call.findings.length > 0 && (
            <span className="text-label text-ink-muted">{call.findings.length}</span>
          )}
        </div>
        {call.findings.map((finding) => (
          <button
            key={finding.id}
            type="button"
            title="Jump to this moment"
            onClick={() => seek(finding.at_seconds)}
            className="grid min-h-14 w-full grid-cols-[48px_16px_minmax(0,1fr)] items-center gap-3 border-0 border-t border-hairline bg-transparent px-6 py-2 text-left hover:bg-wash"
          >
            <span className="text-label text-ink-secondary">{clock(finding.at_seconds)}</span>
            <span className="flex">
              {finding.severity === 'critical' ? (
                <OctagonAlert className="size-4 text-critical" aria-hidden />
              ) : (
                <TriangleAlert className="size-4 text-warning" aria-hidden />
              )}
            </span>
            <span className="flex min-w-0 flex-col">
              <span className="text-body text-ink">{finding.text}</span>
              <span className="text-label text-ink-muted">
                {finding.category} · {foundBy(finding)}
              </span>
            </span>
          </button>
        ))}
        {call.findings.length === 0 && (
          <div className="flex items-center gap-2 border-t border-hairline px-6 pt-4 pb-5 text-ink-secondary">
            <CircleCheck className="size-4 text-passed" aria-hidden />
            No findings on this call
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
        <div className="flex items-baseline gap-3 border-b border-hairline px-6 pt-5 pb-3">
          <h2 className="m-0 text-body font-medium text-ink">Transcript</h2>
        </div>
        <div ref={transcript} className="relative max-h-[560px] overflow-auto py-2">
          {call.entries.map((entry, i) => {
            const on = i === activeIndex;
            const findings = (entry.finding_ids ?? [])
              .map((id) => findingsById[id])
              .filter((f): f is CallScreenFinding => Boolean(f));
            const bad = entry.status === 'failed' || entry.status === 'timed out';
            return (
              <div
                key={i}
                data-entry={i}
                onClick={() => seek(entry.at_seconds)}
                className={cn(
                  'grid cursor-pointer grid-cols-[40px_56px_minmax(0,1fr)] items-start gap-4 px-6 hover:bg-wash',
                  entry.kind === 'tool' ? 'py-1' : 'py-2',
                  on && 'bg-wash shadow-[inset_2px_0_0_var(--color-ink)]'
                )}
              >
                <span className="text-label leading-[22px] text-ink-muted">{clock(entry.at_seconds)}</span>
                {entry.kind === 'turn' ? (
                  <>
                    <span className="text-label leading-[22px] text-ink-secondary">
                      {entry.speaker === 'agent' ? 'Agent' : entry.speaker === 'caller' ? 'Caller' : 'Other'}
                    </span>
                    <div className="flex min-w-0 flex-col items-start gap-1.5">
                      <span className="text-body text-ink">{entry.text}</span>
                      {findings.map((f) => (
                        <FindingChip key={f.id} finding={f} />
                      ))}
                    </div>
                  </>
                ) : (
                  <>
                    <span />
                    <div className="flex min-w-0 flex-col items-start gap-1.5">
                      <button
                        type="button"
                        aria-expanded={Boolean(open[i])}
                        title={open[i] ? 'Hide arguments and result' : 'Show arguments and result'}
                        onClick={(event) => {
                          event.stopPropagation();
                          setOpen((o) => ({ ...o, [i]: !o[i] }));
                        }}
                        className={cn(
                          'inline-flex items-center gap-1.5 border-0 bg-transparent p-0 text-left text-label leading-[22px]',
                          bad ? 'text-critical' : 'text-ink-muted'
                        )}
                      >
                        <Wrench className="size-3.5 flex-none" aria-hidden />
                        <span>{toolLine(entry)}</span>
                        <ChevronRight
                          className={cn('size-3.5 flex-none transition-transform', open[i] && 'rotate-90')}
                          aria-hidden
                        />
                      </button>
                      {open[i] && (
                        <div
                          onClick={(event) => event.stopPropagation()}
                          className="flex w-full max-w-[680px] cursor-default flex-col gap-3 rounded-lg border border-hairline bg-surface-0 px-3.5 py-3"
                        >
                          <Values title="Arguments" values={entry.arguments ?? []} id={`${i}a`} />
                          <Values title="Result" values={entry.result ?? []} id={`${i}r`} />
                          {entry.workflow && (
                            <span className="text-label text-ink-muted">Workflow: {entry.workflow}</span>
                          )}
                        </div>
                      )}
                      {findings.map((f) => (
                        <FindingChip key={f.id} finding={f} />
                      ))}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
