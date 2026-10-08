import { differenceInHours, differenceInMinutes, format } from 'date-fns';

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

/** Turns a fixed-list value such as `caller_hangup` into "Caller hangup". */
export function formatEnumLabel(value: string): string {
  const text = value.replaceAll('_', ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}
