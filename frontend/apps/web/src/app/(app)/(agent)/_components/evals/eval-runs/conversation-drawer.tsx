'use client';

import { useMemo } from 'react';
import { CheckCircle2, MessageSquare, Wrench, XCircle } from 'lucide-react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@workspace/ui/components/ui/accordion';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';
import { cn } from '@workspace/ui/lib/utils';

import { roundScore } from './shared/score-utils';

import type { ConversationTurnOutput, TestCaseResultPublic } from '@/client/types.gen';

interface ConversationDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: TestCaseResultPublic | null;
  testCaseName: string;
  agentName?: string | null;
}

type DisplayItem =
  | { kind: 'user'; content: string; key: string }
  | { kind: 'agent'; content: string; key: string }
  | {
      kind: 'tool_call';
      tool: string;
      params: Record<string, unknown> | null;
      key: string;
    }
  | {
      kind: 'tool_result';
      tool: string;
      result: unknown;
      key: string;
    };

export function ConversationDrawer({
  open,
  onOpenChange,
  result,
  testCaseName,
  agentName,
}: ConversationDrawerProps) {
  const displayItems = useMemo<DisplayItem[]>(() => {
    const turns = result?.transcript ?? [];
    return buildDisplayItems(turns);
  }, [result]);

  if (!result) return null;

  const passed = result.passed === true;
  const score = roundScore(result.verdict?.overall_score);
  const scoreDisplay = score === null ? '—' : score;
  const scoreColorClass = passed ? 'text-green-400' : 'text-red-400';

  const messageCount = displayItems.filter(
    (d) => d.kind === 'user' || d.kind === 'agent'
  ).length;
  const turnCount = Math.ceil(messageCount / 2);
  const toolCallCount = displayItems.filter((d) => d.kind === 'tool_call').length;

  const agentLabel = agentName ? `${agentName} (Agent)` : 'Agent';

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-[520px] flex-col gap-0 border-l border-border bg-background p-0 sm:max-w-[520px]"
      >
        <SheetHeader className="shrink-0 gap-0 space-y-0 border-b border-border px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2">
                <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50">
                  Conversation
                </span>
              </div>
              <SheetTitle className="pr-6 text-sm font-normal leading-snug text-foreground">
                {testCaseName}
              </SheetTitle>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-3 border-t border-border/50 pt-3">
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[10px]',
                passed
                  ? 'border-green-500/20 bg-green-500/10 text-green-400'
                  : 'border-red-500/20 bg-red-500/10 text-red-400'
              )}
            >
              {passed ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
              {passed ? 'Passed' : 'Failed'}
            </span>
            <span className={cn('font-mono text-sm tabular-nums', scoreColorClass)}>
              {scoreDisplay}
              <span className="text-xs text-muted-foreground/40">/100</span>
            </span>
            <div className="h-4 w-px bg-border" />
            <span className="text-xs text-muted-foreground/50">
              <span className="text-foreground tabular-nums">{turnCount}</span> turns
            </span>
            <span className="text-xs text-muted-foreground/50">
              <span className="text-foreground tabular-nums">{toolCallCount}</span> tool calls
            </span>
          </div>
        </SheetHeader>

        <div className="flex-1 space-y-2 overflow-auto px-4 py-4">
          {displayItems.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No transcript available for this result.
            </p>
          ) : (
            displayItems.map((item) => {
              if (item.kind === 'user') {
                return (
                  <div key={item.key} className="flex justify-end">
                    <div className="max-w-[80%]">
                      <div className="rounded-2xl rounded-tr-sm border border-border bg-accent/60 px-3.5 py-2.5">
                        <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
                          {item.content}
                        </p>
                      </div>
                      <p className="mt-1 text-right text-[10px] text-muted-foreground/40">
                        User
                      </p>
                    </div>
                  </div>
                );
              }
              if (item.kind === 'agent') {
                return (
                  <div key={item.key} className="flex justify-start">
                    <div className="max-w-[80%]">
                      <div className="rounded-2xl rounded-tl-sm border border-border bg-background px-3.5 py-2.5">
                        <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
                          {item.content}
                        </p>
                      </div>
                      <p className="ml-1 mt-1 text-[10px] text-muted-foreground/40">
                        {agentLabel}
                      </p>
                    </div>
                  </div>
                );
              }

              if (item.kind === 'tool_call') {
                return (
                  <ToolAccordion
                    key={item.key}
                    itemKey={item.key}
                    variant="request"
                    tool={item.tool}
                    body={item.params ?? {}}
                  />
                );
              }

              return (
                <ToolAccordion
                  key={item.key}
                  itemKey={item.key}
                  variant="result"
                  tool={item.tool}
                  body={item.result}
                />
              );
            })
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function buildDisplayItems(turns: ConversationTurnOutput[]): DisplayItem[] {
  const visibleTurns = turns.filter(
    (t) => t.role !== 'system' && !isPlatformMessage(t.content)
  );

  const toolResultByCallId = new Map<string, string>();
  for (const turn of visibleTurns) {
    if (turn.role === 'tool' && turn.tool_call_id) {
      toolResultByCallId.set(turn.tool_call_id, turn.content ?? '');
    }
  }

  const items: DisplayItem[] = [];
  for (const turn of visibleTurns) {
    if (turn.role === 'user' && turn.content) {
      items.push({ kind: 'user', content: turn.content, key: `u-${turn.index}` });
      continue;
    }
    if (turn.role === 'assistant') {
      if (turn.content) {
        items.push({ kind: 'agent', content: turn.content, key: `a-${turn.index}` });
      }
      for (const call of turn.tool_calls ?? []) {
        const parsed = tryParseJson(call.function.arguments);
        const params =
          parsed && typeof parsed === 'object' && !Array.isArray(parsed)
            ? (parsed as Record<string, unknown>)
            : null;
        items.push({
          kind: 'tool_call',
          tool: call.function.name,
          params,
          key: `tc-${call.id}`,
        });
        const rawResult = toolResultByCallId.get(call.id);
        const resultValue =
          rawResult !== undefined
            ? (tryParseJson(rawResult) ?? rawResult)
            : call.tool_result;
        items.push({
          kind: 'tool_result',
          tool: call.function.name,
          result: resultValue,
          key: `tr-${call.id}`,
        });
      }
    }
  }

  return items;
}

function isPlatformMessage(content: string | null | undefined): boolean {
  return typeof content === 'string' && content.trimStart().startsWith('[platform:');
}

function tryParseJson(raw: unknown): unknown {
  if (typeof raw !== 'string') return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
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

interface ToolAccordionProps {
  itemKey: string;
  variant: 'request' | 'result';
  tool: string;
  body: unknown;
}

function ToolAccordion({ itemKey, variant, tool, body }: ToolAccordionProps) {
  const isRequest = variant === 'request';
  const Icon = isRequest ? Wrench : CheckCircle2;
  const label = isRequest ? 'Tool Request' : 'Tool Result';
  const json = safeStringify(body);

  return (
    <div className="flex justify-center">
      <Accordion
        type="single"
        collapsible
        defaultValue={itemKey}
        className="w-full"
      >
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
              <span className="truncate font-mono text-xs text-foreground/80">
                {tool}
              </span>
            </span>
          </AccordionTrigger>
          <AccordionContent className="px-3 pb-3 pt-3">
            <pre className="whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-foreground/80">
              {json}
            </pre>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
