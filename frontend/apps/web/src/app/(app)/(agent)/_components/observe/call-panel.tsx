'use client';

import { CheckCircle2, Clock, PenLine, Sparkles, Wrench } from 'lucide-react';

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
  buildTranscriptDisplayItems,
  extractTurns,
  formatDate,
  formatDuration,
  formatTimestamp,
  turnStartSeconds,
} from './observe-format';

import type { CallPublic } from '@/client/types.gen';
import type { TranscriptTurn } from './observe-format';

interface CallPanelProps {
  call: CallPublic;
  onCreateTestCaseManual?: (call: CallPublic) => void;
  onCreateTestCaseAi?: (call: CallPublic) => void;
}

export function CallPanel({ call, onCreateTestCaseManual, onCreateTestCaseAi }: CallPanelProps) {
  const turns = extractTurns(call.transcript);
  const displayItems = buildTranscriptDisplayItems(turns);
  const showCreateButton = !!onCreateTestCaseManual || !!onCreateTestCaseAi;

  return (
    <div className="flex h-full w-[480px] shrink-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
        <div className="flex items-start justify-between gap-3 pr-3">
          <p className="text-base text-foreground">{formatDate(call.started_at)}</p>

          {showCreateButton ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex shrink-0 items-center gap-1.5 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-[11px] text-violet-300 transition-all hover:bg-violet-500/20"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Create test case
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                sideOffset={4}
                className="w-56 overflow-hidden rounded-lg border-border bg-background p-0 shadow-xl"
              >
                {onCreateTestCaseManual ? (
                  <DropdownMenuItem
                    onSelect={() => onCreateTestCaseManual(call)}
                    className="flex w-full items-start gap-3 rounded-none border-b border-border px-3 py-3 focus:bg-accent/50"
                  >
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent">
                      <PenLine className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm text-foreground">Manually</p>
                      <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                        Create a test case from scratch
                      </p>
                    </div>
                  </DropdownMenuItem>
                ) : null}
                {onCreateTestCaseAi ? (
                  <DropdownMenuItem
                    onSelect={() => onCreateTestCaseAi(call)}
                    className="flex w-full items-start gap-3 rounded-none px-3 py-3 focus:bg-accent/50"
                  >
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-violet-500/15">
                      <Sparkles className="h-3.5 w-3.5 text-violet-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm text-violet-300">With AI</p>
                      <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                        Describe what to cover, AI builds it
                      </p>
                    </div>
                  </DropdownMenuItem>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : null}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded bg-accent/40 px-2 py-0.5 text-[10px] text-muted-foreground">
            <Clock className="h-3 w-3 shrink-0" />
            {formatDuration(call.duration_seconds)}
          </span>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        <p className="mb-4 text-[10px] uppercase tracking-wider text-muted-foreground">
          Transcript
        </p>
        {displayItems.length === 0 ? (
          <p className="text-xs text-muted-foreground">No transcript available for this call.</p>
        ) : (
          displayItems.map((item) => {
            if (item.kind === 'message') {
              return <TranscriptBubble key={item.key} turn={item.turn} />;
            }
            if (item.kind === 'tool_call') {
              return (
                <ToolAccordionBubble
                  key={item.key}
                  itemKey={item.key}
                  variant="request"
                  tool={item.tool}
                  body={item.params ?? {}}
                  startSeconds={item.startSeconds}
                />
              );
            }
            return (
              <ToolAccordionBubble
                key={item.key}
                itemKey={item.key}
                variant="result"
                tool={item.tool}
                body={item.result}
                startSeconds={item.startSeconds}
              />
            );
          })
        )}
      </div>
    </div>
  );
}

interface ToolAccordionBubbleProps {
  itemKey: string;
  variant: 'request' | 'result';
  tool: string;
  body: unknown;
  startSeconds: number | null;
}

function ToolAccordionBubble({
  itemKey,
  variant,
  tool,
  body,
  startSeconds,
}: ToolAccordionBubbleProps) {
  const isRequest = variant === 'request';
  const timestamp = startSeconds !== null ? formatTimestamp(startSeconds) : null;
  const Icon = isRequest ? Wrench : CheckCircle2;
  const label = isRequest ? 'Tool Request' : 'Tool Result';
  const json = safeStringify(body);

  return (
    <div className="flex flex-col items-center">
      {timestamp ? (
        <span className="mb-1 px-1 text-[9px] tabular-nums text-muted-foreground/40">
          {timestamp}
        </span>
      ) : null}
      <Accordion type="single" collapsible defaultValue={itemKey} className="w-full">
        <AccordionItem
          value={itemKey}
          className="overflow-hidden rounded-lg border border-border bg-accent/10"
        >
          <AccordionTrigger className="px-3 py-2 text-[11px] font-normal text-muted-foreground hover:no-underline data-[state=open]:border-b data-[state=open]:border-border/40">
            <span className="flex min-w-0 items-center gap-2">
              <Icon className="h-3 w-3 shrink-0 text-muted-foreground/60" />
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/60">
                {label}
              </span>
              <span className="truncate font-mono text-[11px] text-foreground/80">{tool}</span>
            </span>
          </AccordionTrigger>
          <AccordionContent className="px-3 pb-3 pt-3">
            <pre className="whitespace-pre-wrap break-all font-mono text-[10px] leading-relaxed text-foreground/80">
              {json}
            </pre>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}

function safeStringify(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function TranscriptBubble({ turn }: { turn: TranscriptTurn }) {
  const role = (turn.role ?? '').toLowerCase();
  const isAgent = role === 'agent' || role === 'assistant';
  const content = turn.content ?? '';
  const start = turnStartSeconds(turn);
  const timestamp = start !== null ? formatTimestamp(start) : null;

  return (
    <div className={cn('flex gap-2.5', isAgent ? 'flex-row' : 'flex-row-reverse')}>
      <div
        className={cn(
          'mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px]',
          isAgent ? 'bg-violet-500/20 text-violet-300' : 'bg-accent/60 text-muted-foreground'
        )}
      >
        {isAgent ? 'AI' : 'C'}
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
          {content}
        </div>
        {timestamp ? (
          <span className="px-1 text-[9px] tabular-nums text-muted-foreground/40">{timestamp}</span>
        ) : null}
      </div>
    </div>
  );
}
