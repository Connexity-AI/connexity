'use client';

import { Wrench } from 'lucide-react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@workspace/ui/components/ui/accordion';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@workspace/ui/components/ui/sheet';
import { cn } from '@workspace/ui/lib/utils';

import { roundScore, scoreColor } from './shared/score-utils';

import type { ConversationTurnOutput, TestCaseResultPublic, ToolCall } from '@/client/types.gen';

interface ConversationDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: TestCaseResultPublic | null;
  testCaseName: string;
}

export function ConversationDrawer({
  open,
  onOpenChange,
  result,
  testCaseName,
}: ConversationDrawerProps) {
  if (!result) return null;

  const score = roundScore(result.verdict?.overall_score);
  const scoreColors = scoreColor(score);
  const turns = result.transcript ?? [];
  const toolCallCount = turns.reduce((acc, t) => acc + (t.tool_calls?.length ?? 0), 0);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-[520px] flex-col gap-0 p-0 sm:max-w-[520px]">
        <SheetHeader className="shrink-0 space-y-2 border-b border-border px-5 py-4">
          <SheetTitle className="text-sm font-medium text-foreground">{testCaseName}</SheetTitle>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span
              className={cn(
                'rounded-full border px-1.5 py-0.5 text-[10px]',
                result.passed
                  ? 'border-green-500/25 bg-green-500/15 text-green-400'
                  : 'border-red-500/25 bg-red-500/15 text-red-400'
              )}
            >
              {result.passed ? 'Passed' : 'Failed'}
            </span>
            <ScorePill score={score} colorClass={scoreColors.text} />
            <span>
              {turns.length} {turns.length === 1 ? 'turn' : 'turns'}
            </span>
            <ToolCallCount count={toolCallCount} />
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-auto px-5 py-4">
          <TranscriptList turns={turns} />
        </div>
      </SheetContent>
    </Sheet>
  );
}

function ScorePill({ score, colorClass }: { score: number | null; colorClass: string }) {
  if (score === null) return null;

  return <span className={cn('font-mono tabular-nums', colorClass)}>{score}/100</span>;
}

function ToolCallCount({ count }: { count: number }) {
  if (count <= 0) return null;

  return (
    <span>
      {count} tool {count === 1 ? 'call' : 'calls'}
    </span>
  );
}

function TranscriptList({ turns }: { turns: ConversationTurnOutput[] }) {
  if (turns.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">No transcript available for this result.</p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {turns.map((turn) => (
        <TranscriptTurn key={`${turn.index}-${turn.role}`} turn={turn} />
      ))}
    </ul>
  );
}

function TranscriptTurn({ turn }: { turn: ConversationTurnOutput }) {
  const role = turn.role;

  if (role === 'user') {
    return (
      <li className="flex justify-end">
        <div className="max-w-[85%] rounded-lg bg-accent/60 px-3 py-2 text-sm text-foreground">
          {turn.content ?? ''}
        </div>
      </li>
    );
  }

  if (role === 'system') {
    return (
      <li className="flex">
        <div className="max-w-full rounded-md border border-border/60 bg-background px-3 py-2 text-xs text-muted-foreground">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
            system
          </span>
          <div className="mt-1 whitespace-pre-wrap">{turn.content ?? ''}</div>
        </div>
      </li>
    );
  }

  if (role === 'tool') {
    return (
      <li className="flex">
        <ToolResultTurn turn={turn} />
      </li>
    );
  }

  return (
    <li className="flex flex-col gap-2">
      <AssistantContent content={turn.content} />
      <AssistantToolCalls toolCalls={turn.tool_calls} />
    </li>
  );
}

function AssistantContent({ content }: { content: string | null | undefined }) {
  if (!content) return null;

  return (
    <div className="max-w-[85%] rounded-lg bg-background px-3 py-2 text-sm text-foreground">
      {content}
    </div>
  );
}

function AssistantToolCalls({ toolCalls }: { toolCalls: ToolCall[] | null | undefined }) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="flex flex-col gap-1.5">
      {toolCalls.map((tc) => (
        <ToolCallBlock key={tc.id} toolCall={tc} />
      ))}
    </div>
  );
}

function ToolCallBlock({ toolCall }: { toolCall: ToolCall }) {
  const parsedArgs = parseToolCallArgs(toolCall.function.arguments);

  return (
    <Accordion
      type="single"
      collapsible
      className="rounded-md border border-border/60 bg-accent/20 text-xs"
    >
      <AccordionItem value="tool-call" className="border-b-0">
        <AccordionTrigger className="flex items-center gap-2 px-3 py-2 font-normal text-muted-foreground hover:text-foreground hover:no-underline">
          <Wrench className="h-3 w-3 shrink-0" />
          <span className="flex-1 text-left font-mono text-foreground">
            {toolCall.function.name}
          </span>
        </AccordionTrigger>
        <AccordionContent className="flex flex-col gap-2 border-t border-border/60 px-3 pb-3 pt-2">
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/60">
              Arguments
            </div>
            <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded bg-background/60 p-2 font-mono text-[11px] text-foreground">
              {typeof parsedArgs === 'string' ? parsedArgs : JSON.stringify(parsedArgs, null, 2)}
            </pre>
          </div>
          <ToolCallResult result={toolCall.tool_result} />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

function parseToolCallArgs(raw: unknown): unknown {
  if (typeof raw !== 'string') return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function ToolCallResult({ result }: { result: ToolCall['tool_result'] }) {
  if (result == null) return null;
  return (
    <div>
      <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/60">
        Result
      </div>
      <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded bg-background/60 p-2 font-mono text-[11px] text-foreground">
        {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
      </pre>
    </div>
  );
}

function ToolResultTurn({ turn }: { turn: ConversationTurnOutput }) {
  return (
    <Accordion
      type="single"
      collapsible
      className="w-full rounded-md border border-border/60 bg-background text-xs"
    >
      <AccordionItem value="tool-result" className="border-b-0">
        <AccordionTrigger className="flex items-center gap-2 px-3 py-2 font-normal text-muted-foreground hover:text-foreground hover:no-underline">
          <span className="flex-1 text-left text-[10px] uppercase tracking-wider text-muted-foreground/60">
            tool result
          </span>
        </AccordionTrigger>
        <AccordionContent className="border-t border-border/60 px-0 pb-0 pt-0">
          <pre className="max-h-60 overflow-auto whitespace-pre-wrap px-3 py-2 font-mono text-[11px] text-foreground">
            {turn.content ?? ''}
          </pre>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
