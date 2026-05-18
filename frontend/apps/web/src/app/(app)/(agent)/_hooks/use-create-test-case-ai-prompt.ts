'use client';

import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type KeyboardEvent,
  type RefObject,
  type SetStateAction,
} from 'react';

import { useRunTestCaseAiAgent } from '@/app/(app)/(agent)/_hooks/use-run-test-case-ai-agent';
import {
  TurnRole,
  type CallPublic,
  type ConversationTurnInput,
  type TestCasePublic,
  type ToolCall,
} from '@/client/types.gen';
import { isErrorApiResult } from '@/utils/api';

import type { CarouselApi } from '@workspace/ui/components/ui/carousel';

export const STAGES = [
  { label: 'Reading conversation transcript…', duration: 2000 },
  { label: 'Reading agent prompt…', duration: 2200 },
  { label: 'Analysing existing test cases…', duration: 3000 },
  { label: 'Generating persona and scenario…', duration: 3600 },
  { label: 'Building expected outcomes…', duration: 2600 },
  { label: 'Finalising test case…', duration: 1600 },
];

const TICK_MS = 30;
const HOLD_PROGRESS_AT = 95;
const COMPLETION_DELAY_MS = 200;

export type AiPromptPhase = 'input' | 'generating' | 'results';

interface RawToolCall {
  id?: unknown;
  function?: {
    name?: unknown;
    arguments?: unknown;
  };
  tool_result?: unknown;
}

interface RawTranscriptEntry {
  role?: unknown;
  content?: unknown;
  message?: unknown;
  name?: unknown;
  tool_call_id?: unknown;
  toolCallId?: unknown;
  arguments?: unknown;
  result?: unknown;
  toolCalls?: RawToolCall[];
  tool_calls?: RawToolCall[];
  start?: unknown;
  timestamp?: unknown;
  secondsFromStart?: unknown;
}

interface UseCreateTestCaseAiPromptArgs {
  agentId: string;
  call: CallPublic;
  onClose: () => void;
}

export interface UseCreateTestCaseAiPromptReturn {
  phase: AiPromptPhase;
  userPrompt: string;
  setUserPrompt: Dispatch<SetStateAction<string>>;
  stageIndex: number;
  progress: number;
  error: string | null;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  isPending: boolean;
  handleGenerate: () => Promise<void>;
  handleKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  generatedTestCases: TestCasePublic[];
  setCarouselApi: Dispatch<SetStateAction<CarouselApi | undefined>>;
  currentIndex: number;
  canScrollPrev: boolean;
  canScrollNext: boolean;
  scrollPrev: () => void;
  scrollNext: () => void;
}

function normalizeRole(raw: unknown): TurnRole {
  if (typeof raw !== 'string') return TurnRole.USER;
  const lower = raw.toLowerCase();
  if (lower === 'assistant' || lower === 'agent') return TurnRole.ASSISTANT;
  if (lower === 'system') return TurnRole.SYSTEM;
  if (lower === 'tool') return TurnRole.TOOL;
  return TurnRole.USER;
}

function extractOffsetSeconds(entry: Record<string, unknown>): number | null {
  if (typeof entry.secondsFromStart === 'number') return entry.secondsFromStart;
  if (typeof entry.start === 'number') return entry.start;
  if (typeof entry.timestamp === 'number') return entry.timestamp;
  return null;
}

function stringifyToolArguments(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return '{}';
    }
  }
  return '{}';
}

function stringifyToolResult(value: unknown): string | null {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return null;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function textContent(entry: RawTranscriptEntry): string | null {
  if (typeof entry.content === 'string') return entry.content;
  if (typeof entry.message === 'string') return entry.message;
  return null;
}

function toolCallId(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function toToolCall(raw: RawToolCall, fallbackId: string): ToolCall | null {
  const name = raw.function?.name;
  if (typeof name !== 'string' || !name.trim()) return null;

  return {
    id: toolCallId(raw.id, fallbackId),
    type: 'function',
    function: {
      name,
      arguments: stringifyToolArguments(raw.function?.arguments),
    },
    tool_result: raw.tool_result ?? null,
  };
}

function rawToolCalls(entry: RawTranscriptEntry): RawToolCall[] {
  if (Array.isArray(entry.toolCalls)) return entry.toolCalls;
  if (Array.isArray(entry.tool_calls)) return entry.tool_calls;
  return [];
}

function buildTranscriptFromCall(call: CallPublic): ConversationTurnInput[] {
  const raw = call.transcript;
  if (!Array.isArray(raw)) return [];

  const startedAtMs = new Date(call.started_at).getTime();
  const turns: ConversationTurnInput[] = [];

  for (const [rawIndex, entry] of raw.entries()) {
    if (!entry || typeof entry !== 'object') continue;

    const rawEntry = entry as RawTranscriptEntry;
    const roleRaw = typeof rawEntry.role === 'string' ? rawEntry.role.toLowerCase() : '';

    const offsetSeconds = extractOffsetSeconds(entry);
    let timestampMs = startedAtMs + rawIndex;
    if (offsetSeconds !== null) {
      timestampMs = startedAtMs + offsetSeconds * 1000;
    }
    const timestamp = new Date(timestampMs).toISOString();

    if (roleRaw === 'tool_calls') {
      const calls = rawToolCalls(rawEntry)
        .map((callItem, callIndex) => toToolCall(callItem, `call_${rawIndex}_${callIndex}`))
        .filter((callItem): callItem is ToolCall => callItem !== null);
      if (calls.length > 0) {
        turns.push({
          index: turns.length,
          role: TurnRole.ASSISTANT,
          content: textContent(rawEntry),
          tool_calls: calls,
          timestamp,
        });
      }
      continue;
    }

    if (roleRaw === 'tool_call_invocation' || roleRaw === 'tool_call') {
      const name = typeof rawEntry.name === 'string' ? rawEntry.name : null;
      if (name) {
        const id = toolCallId(rawEntry.tool_call_id ?? rawEntry.toolCallId, `call_${rawIndex}`);
        turns.push({
          index: turns.length,
          role: TurnRole.ASSISTANT,
          content: textContent(rawEntry),
          tool_calls: [
            {
              id,
              type: 'function',
              function: {
                name,
                arguments: stringifyToolArguments(rawEntry.arguments),
              },
            },
          ],
          timestamp,
        });
      }
      continue;
    }

    if (roleRaw === 'tool_call_result' || roleRaw === 'tool_result') {
      turns.push({
        index: turns.length,
        role: TurnRole.TOOL,
        content: stringifyToolResult(rawEntry.result ?? rawEntry.content),
        tool_call_id: toolCallId(rawEntry.tool_call_id ?? rawEntry.toolCallId, `call_${rawIndex}`),
        timestamp,
      });
      continue;
    }

    turns.push({
      index: turns.length,
      role: normalizeRole(rawEntry.role),
      content: textContent(rawEntry),
      timestamp,
    });
  }

  return turns;
}

export function useCreateTestCaseAiPrompt({
  agentId,
  call,
  onClose,
}: UseCreateTestCaseAiPromptArgs): UseCreateTestCaseAiPromptReturn {
  const [phase, setPhase] = useState<AiPromptPhase>('input');
  const [userPrompt, setUserPrompt] = useState('');
  const [stageIndex, setStageIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [generatedTestCases, setGeneratedTestCases] = useState<TestCasePublic[]>([]);
  const [carouselApi, setCarouselApi] = useState<CarouselApi | undefined>();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const frameRef = useRef<number | null>(null);

  const { mutateAsync, isPending } = useRunTestCaseAiAgent(agentId);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, []);

  useEffect(() => {
    if (!carouselApi) return;
    const sync = () => {
      setCurrentIndex(carouselApi.selectedScrollSnap());
      setCanScrollPrev(carouselApi.canScrollPrev());
      setCanScrollNext(carouselApi.canScrollNext());
    };
    sync();
    carouselApi.on('select', sync);
    carouselApi.on('reInit', sync);
    return () => {
      carouselApi.off('select', sync);
      carouselApi.off('reInit', sync);
    };
  }, [carouselApi]);

  const startStageAnimation = () => {
    setStageIndex(0);
    setProgress(0);
    let elapsed = 0;
    const total = STAGES.reduce((s, st) => s + st.duration, 0);
    const lastStageIndex = STAGES.length - 1;

    const runStage = (idx: number) => {
      const stage = STAGES[idx];
      if (!stage) return;
      setStageIndex(idx);
      const end = elapsed + stage.duration;

      const tick = () => {
        elapsed += TICK_MS;
        const computed = Math.min(100, Math.round((elapsed / total) * 100));
        setProgress(idx === lastStageIndex ? Math.min(HOLD_PROGRESS_AT, computed) : computed);
        if (elapsed < end) {
          frameRef.current = requestAnimationFrame(tick);
        } else {
          elapsed = end;
          if (idx < lastStageIndex) {
            runStage(idx + 1);
          } else {
            setProgress(HOLD_PROGRESS_AT);
            frameRef.current = null;
          }
        }
      };
      frameRef.current = requestAnimationFrame(tick);
    };

    runStage(0);
  };

  const cancelAnimation = () => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
  };

  const handleGenerate = async () => {
    const prompt = userPrompt.trim();
    if (!prompt) return;
    setError(null);
    setPhase('generating');
    startStageAnimation();

    const transcript = buildTranscriptFromCall(call);
    const result = await mutateAsync({
      prompt,
      sourceCallId: call.id,
      transcript: transcript.length > 0 ? transcript : null,
    });
    cancelAnimation();

    if (isErrorApiResult(result)) {
      setPhase('input');
      setStageIndex(0);
      setProgress(0);
      setError('AI generation failed. Try again.');
      return;
    }

    setProgress(100);

    const created = result.data?.created ?? [];
    setTimeout(() => {
      if (created.length === 0) {
        onClose();
        return;
      }
      setGeneratedTestCases(created);
      setCurrentIndex(0);
      setPhase('results');
    }, COMPLETION_DELAY_MS);
  };

  const scrollPrev = () => carouselApi?.scrollPrev();
  const scrollNext = () => carouselApi?.scrollNext();

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void handleGenerate();
    }
  };

  return {
    phase,
    userPrompt,
    setUserPrompt,
    stageIndex,
    progress,
    error,
    textareaRef,
    isPending,
    handleGenerate,
    handleKeyDown,
    generatedTestCases,
    setCarouselApi,
    currentIndex,
    canScrollPrev,
    canScrollNext,
    scrollPrev,
    scrollNext,
  };
}
