'use client';

import { useMemo, useState } from 'react';
import { CheckCircle2, ChevronDown, MessageSquare, Wrench, XCircle } from 'lucide-react';

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
      kind: 'tool_pair';
      tool: string;
      params: Record<string, unknown> | null;
      result: string;
      key: string;
    };

export function ConversationDrawer({
  open,
  onOpenChange,
  result,
  testCaseName,
  agentName,
}: ConversationDrawerProps) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  const turns = result?.transcript ?? [];

  const displayItems = useMemo<DisplayItem[]>(() => buildDisplayItems(turns), [turns]);

  const toggleTool = (key: string) => {
    setExpandedTools((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (!result) return null;

  const passed = result.passed === true;
  const score = roundScore(result.verdict?.overall_score);
  const scoreDisplay = score === null ? '—' : score;
  const scoreColorClass = passed ? 'text-green-400' : 'text-red-400';

  const messageCount = displayItems.filter(
    (d) => d.kind === 'user' || d.kind === 'agent'
  ).length;
  const turnCount = Math.ceil(messageCount / 2);
  const toolCallCount = displayItems.filter((d) => d.kind === 'tool_pair').length;

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

              const isOpen = expandedTools.has(item.key);
              const resultObject = parseJsonObject(item.result);
              const paramsEntries = item.params ? Object.entries(item.params) : [];

              return (
                <div key={item.key} className="flex justify-center">
                  <button
                    type="button"
                    onClick={() => toggleTool(item.key)}
                    className={cn(
                      'w-full max-w-[88%] rounded-lg border text-left transition-colors',
                      isOpen
                        ? 'border-border bg-accent/30'
                        : 'border-border/50 bg-accent/10 hover:border-border hover:bg-accent/20'
                    )}
                  >
                    <div className="flex items-center gap-2 px-3 py-2">
                      <Wrench className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                      <span className="flex-1 truncate font-mono text-[11px] text-muted-foreground">
                        {item.tool}
                        {paramsEntries.length > 0 && (
                          <span className="ml-1 text-muted-foreground/40">
                            (
                            {paramsEntries
                              .map(([k, v]) => `${k}: "${formatParamValue(v)}"`)
                              .join(', ')}
                            )
                          </span>
                        )}
                      </span>
                      <ChevronDown
                        className={cn(
                          'h-3 w-3 shrink-0 text-muted-foreground/40 transition-transform duration-150',
                          isOpen && 'rotate-180'
                        )}
                      />
                    </div>
                    {isOpen && (
                      <div className="border-t border-border/40 px-3 pb-3 pt-2">
                        <p className="mb-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/50">
                          Response
                        </p>
                        {resultObject ? (
                          <div className="space-y-1">
                            {Object.entries(resultObject).map(([k, v]) => (
                              <div key={k} className="flex items-start gap-2">
                                <span className="shrink-0 font-mono text-[11px] text-muted-foreground/60">
                                  {k}:
                                </span>
                                <span className="break-all font-mono text-[11px] text-foreground/80">
                                  {formatResultValue(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <pre className="whitespace-pre-wrap break-all font-mono text-[11px] text-foreground/70">
                            {item.result}
                          </pre>
                        )}
                      </div>
                    )}
                  </button>
                </div>
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
          kind: 'tool_pair',
          tool: call.function.name,
          params,
          result: toolResultByCallId.get(call.id) ?? stringifyToolResult(call.tool_result),
          key: `t-${call.id}`,
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

function parseJsonObject(raw: string): Record<string, unknown> | null {
  const parsed = tryParseJson(raw);
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    return parsed as Record<string, unknown>;
  }
  return null;
}

function stringifyToolResult(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function formatParamValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function formatResultValue(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map((v) => String(v)).join(', ')}]`;
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
