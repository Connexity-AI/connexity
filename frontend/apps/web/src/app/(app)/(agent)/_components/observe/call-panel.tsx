'use client';

import { AlertTriangle, CheckCircle2, Clock, PhoneOff, Tag, Wrench, X } from 'lucide-react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@workspace/ui/components/ui/accordion';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';
import { cn } from '@workspace/ui/lib/utils';

import {
  useCallTrace,
  useRefreshCallExecutions,
  useSetCallLabel,
} from '@/app/(app)/(agent)/_hooks/use-calls';
import {
  CallLabel,
  ExecutionMatch,
  ExecutionStatus,
  Speaker,
  ToolCallStatus,
} from '@/client/types.gen';
import { CallLabelChip } from './call-label-chip';
import { formatDate, formatDuration, formatEnumLabel, formatTimestamp } from './observe-format';

import type {
  CallPublic,
  Execution,
  ExecutionStep,
  MarkerEvent,
  ToolCallEvent,
  TraceOutput,
  UtteranceEvent,
} from '@/client/types.gen';

interface CallPanelProps {
  agentId: string;
  call: CallPublic;
}

export function CallPanel({ agentId, call }: CallPanelProps) {
  const traceQuery = useCallTrace(call.id, call.has_trace);
  const trace = traceQuery.data?.trace ?? null;
  const executions = traceQuery.data?.executions ?? [];
  const refreshExecutions = useRefreshCallExecutions(call.id);
  const hasToolCalls = trace?.events.some((event) => event.type === 'tool_call') ?? false;

  const setLabel = useSetCallLabel(agentId);
  const currentLabel = call.label ?? null;

  return (
    <div className="flex h-full w-[480px] shrink-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
        <div className="flex items-start justify-between gap-3 pr-3">
          <p className="text-base text-foreground">{formatDate(call.started_at)}</p>

          <div className="flex shrink-0 items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  disabled={setLabel.isPending}
                  className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border bg-accent/20 px-2.5 py-1.5 text-[11px] text-muted-foreground transition-all hover:bg-accent/40 disabled:opacity-60"
                >
                  {currentLabel === null ? (
                    <>
                      <Tag className="h-3.5 w-3.5" />
                      Set label
                    </>
                  ) : (
                    <CallLabelChip label={currentLabel} />
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                sideOffset={4}
                className="w-44 overflow-hidden rounded-lg border-border bg-background p-0 shadow-xl"
              >
                <DropdownMenuItem
                  onSelect={() => setLabel.mutate({ callId: call.id, label: CallLabel.GOOD })}
                  className="flex items-center gap-2 rounded-none border-b border-border px-3 py-2 focus:bg-accent/50"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-sm text-foreground">Good</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={() => setLabel.mutate({ callId: call.id, label: CallLabel.BAD })}
                  className="flex items-center gap-2 rounded-none px-3 py-2 focus:bg-accent/50"
                >
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
                  <span className="text-sm text-foreground">Bad</span>
                </DropdownMenuItem>
                {currentLabel !== null ? (
                  <DropdownMenuItem
                    onSelect={() => setLabel.mutate({ callId: call.id, label: null })}
                    className="flex items-center gap-2 rounded-none border-t border-border px-3 py-2 focus:bg-accent/50"
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Clear</span>
                  </DropdownMenuItem>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded bg-accent/40 px-2 py-0.5 text-[10px] text-muted-foreground">
            <Clock className="h-3 w-3 shrink-0" />
            {formatDuration(call.duration_seconds)}
          </span>
          {call.end_reason ? (
            <span
              className="inline-flex items-center gap-1 rounded bg-accent/40 px-2 py-0.5 text-[10px] text-muted-foreground"
              title={call.end_reason_detail ?? undefined}
            >
              <PhoneOff className="h-3 w-3 shrink-0" />
              {formatEnumLabel(call.end_reason)}
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        <div className="mb-4 flex items-center justify-between gap-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Conversation</p>
          {hasToolCalls ? (
            <button
              type="button"
              disabled={refreshExecutions.isPending}
              onClick={() => refreshExecutions.mutate()}
              className="text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline disabled:opacity-60"
              title="Look in the mapped backends for what happened behind each tool call"
            >
              {refreshExecutions.isPending ? 'Looking…' : 'Find executions'}
            </button>
          ) : null}
        </div>
        {refreshExecutions.data ? (
          <p className="text-[10px] text-muted-foreground">
            {refreshExecutions.data.matched} of {refreshExecutions.data.mapped} mapped tool calls
            have an execution.
            {refreshExecutions.data.problems?.[0] ? ` ${refreshExecutions.data.problems[0]}` : ''}
          </p>
        ) : null}
        <CallEvents
          hasTrace={call.has_trace}
          isLoading={traceQuery.isLoading}
          trace={trace}
          executions={executions}
        />
      </div>
    </div>
  );
}

interface CallEventsProps {
  hasTrace: boolean;
  isLoading: boolean;
  trace: TraceOutput | null;
  executions: Execution[];
}

function CallEvents({ hasTrace, isLoading, trace, executions }: CallEventsProps) {
  if (!hasTrace) {
    return (
      <p className="text-xs text-muted-foreground">
        This call has not been converted to a trace yet, so its conversation cannot be shown.
      </p>
    );
  }
  if (isLoading) {
    return <p className="text-xs text-muted-foreground">Loading…</p>;
  }
  if (!trace) {
    return <p className="text-xs text-muted-foreground">The trace could not be loaded.</p>;
  }
  if (trace.events.length === 0) {
    return <p className="text-xs text-muted-foreground">Nothing was said on this call.</p>;
  }
  return trace.events.map((event) => {
    if (event.type === 'utterance') return <UtteranceBubble key={event.id} event={event} />;
    if (event.type === 'tool_call') {
      return (
        <ToolCallBlock
          key={event.id}
          event={event}
          execution={executions.find((execution) => execution.event_id === event.id)}
        />
      );
    }
    if (event.type === 'marker') return <MarkerLine key={event.id} event={event} />;
    return null;
  });
}

function eventTimestamp(startMs: number | null | undefined): string | null {
  return typeof startMs === 'number' ? formatTimestamp(startMs / 1000) : null;
}

const TOOL_STATUS_STYLES: Record<ToolCallStatus, string> = {
  [ToolCallStatus.OK]: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400',
  [ToolCallStatus.ERROR]: 'border-rose-500/25 bg-rose-500/10 text-rose-400',
  [ToolCallStatus.TIMEOUT]: 'border-rose-500/25 bg-rose-500/10 text-rose-400',
  [ToolCallStatus.NO_RESULT]: 'border-border bg-accent/30 text-muted-foreground',
};

interface ToolCallBlockProps {
  event: ToolCallEvent;
  execution?: Execution;
}

function ToolCallBlock({ event, execution }: ToolCallBlockProps) {
  const timestamp = eventTimestamp(event.start_ms);
  const status = event.status ?? null;
  const hasResult = event.result !== null && event.result !== undefined;

  return (
    <div className="flex flex-col items-center">
      {timestamp ? (
        <span className="mb-1 px-1 text-[9px] tabular-nums text-muted-foreground/40">
          {timestamp}
        </span>
      ) : null}
      <Accordion type="single" collapsible className="w-full">
        <AccordionItem
          value={event.id}
          className="overflow-hidden rounded-lg border border-border bg-accent/10"
        >
          <AccordionTrigger className="px-3 py-2 text-[11px] font-normal text-muted-foreground hover:no-underline data-[state=open]:border-b data-[state=open]:border-border/40">
            <span className="flex min-w-0 items-center gap-2">
              <Wrench className="h-3 w-3 shrink-0 text-muted-foreground/60" />
              <span className="truncate font-mono text-[11px] text-foreground/80">
                {event.name}
              </span>
              {status ? (
                <span
                  className={cn(
                    'shrink-0 rounded border px-1.5 py-px text-[10px]',
                    TOOL_STATUS_STYLES[status]
                  )}
                >
                  {formatEnumLabel(status)}
                </span>
              ) : null}
              {execution ? (
                <span className="shrink-0 rounded border border-border px-1.5 py-px text-[10px] text-muted-foreground">
                  {execution.steps?.length ?? 0} steps
                </span>
              ) : null}
            </span>
          </AccordionTrigger>
          <AccordionContent className="space-y-3 px-3 pb-3 pt-3">
            <ToolCallSection label="Arguments" value={event.arguments ?? null} empty="None" />
            <ToolCallSection
              label="Result"
              value={hasResult ? event.result : null}
              empty="No result was logged"
            />
            {execution ? <ExecutionDetail execution={execution} /> : null}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}

const EXECUTION_STATUS_STYLES: Record<ExecutionStatus, string> = {
  [ExecutionStatus.OK]: 'bg-emerald-400',
  [ExecutionStatus.ERROR]: 'bg-rose-400',
  [ExecutionStatus.RUNNING]: 'bg-amber-400',
  [ExecutionStatus.CANCELED]: 'bg-muted-foreground',
  [ExecutionStatus.UNKNOWN]: 'bg-muted-foreground',
};

function ExecutionDetail({ execution }: { execution: Execution }) {
  const steps = execution.steps ?? [];
  return (
    <div>
      <p className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground/60">
        Execution
      </p>
      <p className="mb-2 text-[10px] text-muted-foreground">
        {execution.workflow_name ?? execution.workflow_id ?? execution.provider}
        {' · '}
        {formatEnumLabel(execution.status ?? ExecutionStatus.UNKNOWN)}
        {execution.match === ExecutionMatch.GUESS ? (
          <span
            className="ml-1.5 rounded border border-amber-500/30 bg-amber-500/10 px-1 py-px text-amber-400"
            title="The backend received no call id, so this was matched on arguments and time only"
          >
            Guess
          </span>
        ) : null}
      </p>
      {steps.length === 0 ? (
        <p className="text-[10px] text-muted-foreground/60">The backend kept no step data.</p>
      ) : (
        <ol className="space-y-1">
          {steps.map((step, index) => (
            <ExecutionStepRow key={`${step.name}-${index}`} step={step} />
          ))}
        </ol>
      )}
    </div>
  );
}

function ExecutionStepRow({ step }: { step: ExecutionStep }) {
  const status = step.status ?? ExecutionStatus.OK;
  const hasOutput = step.output !== null && step.output !== undefined;
  const hasError = step.error !== null && step.error !== undefined;
  const inputFrom = step.input_from ?? [];

  return (
    <li>
      <details className="rounded border border-border/60 bg-background/40">
        <summary className="flex cursor-pointer items-center gap-2 px-2 py-1.5 text-[11px]">
          <span
            className={cn('h-1.5 w-1.5 shrink-0 rounded-full', EXECUTION_STATUS_STYLES[status])}
          />
          <span className="truncate text-foreground/90">{step.name}</span>
          {step.kind ? (
            <span className="shrink-0 font-mono text-[10px] text-muted-foreground/60">
              {step.kind}
            </span>
          ) : null}
          {typeof step.duration_ms === 'number' ? (
            <span className="ml-auto shrink-0 tabular-nums text-[10px] text-muted-foreground/60">
              {step.duration_ms} ms
            </span>
          ) : null}
        </summary>
        <div className="space-y-2 border-t border-border/40 px-2 py-2">
          {inputFrom.length > 0 ? (
            <p className="text-[10px] text-muted-foreground">
              Input: the output of {inputFrom.join(', ')}
            </p>
          ) : null}
          {hasError ? <ToolCallSection label="Error" value={step.error} empty="" /> : null}
          {hasOutput ? (
            <ToolCallSection label="Output" value={step.output} empty="" />
          ) : (
            <p className="text-[10px] text-muted-foreground/60">
              {step.data_dropped
                ? 'Output not kept: the execution was over the size limit.'
                : 'No output.'}
            </p>
          )}
        </div>
      </details>
    </li>
  );
}

interface ToolCallSectionProps {
  label: string;
  value: unknown;
  empty: string;
}

function ToolCallSection({ label, value, empty }: ToolCallSectionProps) {
  return (
    <div>
      <p className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground/60">
        {label}
      </p>
      {value === null ? (
        <p className="text-[10px] text-muted-foreground/60">{empty}</p>
      ) : (
        <pre className="whitespace-pre-wrap break-all font-mono text-[10px] leading-relaxed text-foreground/80">
          {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
        </pre>
      )}
    </div>
  );
}

function MarkerLine({ event }: { event: MarkerEvent }) {
  const timestamp = eventTimestamp(event.start_ms);
  return (
    <div
      className="flex items-center gap-2 text-[10px] text-muted-foreground/60"
      title={event.detail ? JSON.stringify(event.detail, null, 2) : undefined}
    >
      <span className="h-px flex-1 bg-border/60" />
      <span className="font-mono">{event.name}</span>
      {timestamp ? <span className="tabular-nums">{timestamp}</span> : null}
      <span className="h-px flex-1 bg-border/60" />
    </div>
  );
}

const SPEAKER_BADGES: Record<Speaker, string> = {
  [Speaker.AGENT]: 'AI',
  [Speaker.CALLER]: 'C',
  [Speaker.OTHER]: '3rd',
};

function UtteranceBubble({ event }: { event: UtteranceEvent }) {
  const isAgent = event.speaker === Speaker.AGENT;
  const timestamp = eventTimestamp(event.start_ms);

  return (
    <div className={cn('flex gap-2.5', isAgent ? 'flex-row' : 'flex-row-reverse')}>
      <div
        className={cn(
          'mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px]',
          isAgent ? 'bg-violet-500/20 text-violet-300' : 'bg-accent/60 text-muted-foreground'
        )}
      >
        {SPEAKER_BADGES[event.speaker]}
      </div>
      <div
        className={cn('max-w-[80%] space-y-1', isAgent ? 'items-start' : 'flex flex-col items-end')}
      >
        <div
          className={cn(
            'whitespace-pre-wrap rounded-xl px-3 py-2 text-[11px] leading-relaxed',
            isAgent
              ? 'rounded-tl-sm bg-violet-500/10 text-foreground/90'
              : 'rounded-tr-sm bg-accent/50 text-foreground/80'
          )}
        >
          {event.text}
        </div>
        {timestamp ? (
          <span className="px-1 text-[9px] tabular-nums text-muted-foreground/40">{timestamp}</span>
        ) : null}
      </div>
    </div>
  );
}
