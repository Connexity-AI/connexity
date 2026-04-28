import { differenceInHours, differenceInMinutes, format } from 'date-fns';

export interface TranscriptTurn {
  role?: string;
  content?: string;
  words?: Array<{ start?: number; end?: number; word?: string }>;
  start?: number;
  timestamp?: number | string;
}

export type TranscriptDisplayItem =
  | { kind: 'message'; turn: TranscriptTurn; key: string }
  | {
      kind: 'tool_call';
      tool: string;
      params: Record<string, unknown> | null;
      startSeconds: number | null;
      key: string;
    }
  | {
      kind: 'tool_result';
      tool: string;
      result: unknown;
      startSeconds: number | null;
      key: string;
    };

export function extractTurns(raw: unknown): TranscriptTurn[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter((t): t is TranscriptTurn => typeof t === 'object' && t !== null);
}

interface RawTranscriptItem {
  role?: string;
  content?: unknown;
  name?: string;
  tool_call_id?: string;
  arguments?: unknown;
  result?: unknown;
  words?: Array<{ start?: number; end?: number; word?: string }>;
  start?: number;
  timestamp?: number | string;
}

function toTurn(item: RawTranscriptItem): TranscriptTurn {
  return {
    role: item.role,
    content: typeof item.content === 'string' ? item.content : undefined,
    words: item.words,
    start: item.start,
    timestamp: item.timestamp,
  };
}

function parseArgs(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      // fall through
    }
  }
  return null;
}

function parseResult(value: unknown): unknown {
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  return value;
}

function itemStartSeconds(item: RawTranscriptItem): number | null {
  const firstWordStart = item.words?.[0]?.start;
  if (typeof firstWordStart === 'number') return firstWordStart;
  if (typeof item.start === 'number') return item.start;
  if (typeof item.timestamp === 'number') return item.timestamp;
  return null;
}

export function buildTranscriptDisplayItems(
  turns: TranscriptTurn[],
): TranscriptDisplayItem[] {
  const items: TranscriptDisplayItem[] = [];
  (turns as RawTranscriptItem[]).forEach((item, idx) => {
    const role = (item.role ?? '').toLowerCase();
    const start = itemStartSeconds(item);

    if (role === 'tool_call_invocation' || role === 'tool_call') {
      items.push({
        kind: 'tool_call',
        tool: item.name ?? 'tool',
        params: parseArgs(item.arguments),
        startSeconds: start,
        key: `tc-${item.tool_call_id ?? idx}`,
      });
      return;
    }

    if (role === 'tool_call_result' || role === 'tool_result') {
      items.push({
        kind: 'tool_result',
        tool: item.name ?? 'tool',
        result: parseResult(item.result ?? item.content),
        startSeconds: start,
        key: `tr-${item.tool_call_id ?? idx}`,
      });
      return;
    }

    items.push({ kind: 'message', turn: toTurn(item), key: `m-${idx}` });
  });

  return items;
}

/** Returns the message start time in seconds, or null if not derivable. */
export function turnStartSeconds(turn: TranscriptTurn): number | null {
  const firstWordStart = turn.words?.[0]?.start;
  if (typeof firstWordStart === 'number') return firstWordStart;
  if (typeof turn.start === 'number') return turn.start;
  if (typeof turn.timestamp === 'number') return turn.timestamp;
  return null;
}

/** Formats seconds as `m:ss` (e.g. 65 → "1:05"). */
export function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatRelativeDay(date: Date): string {
  const now = new Date();
  const mins = differenceInMinutes(now, date);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = differenceInHours(now, date);
  if (hrs < 24) return `${hrs}h ago`;
  return format(date, 'MMM d, yyyy');
}

function formatClockTime(date: Date): string {
  return format(date, 'h:mm a');
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return `${formatRelativeDay(date)} · ${formatClockTime(date)}`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}
