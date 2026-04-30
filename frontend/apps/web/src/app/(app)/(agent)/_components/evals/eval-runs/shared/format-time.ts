import { formatDistanceToNowStrict } from 'date-fns';

// Backend serializes naive UTC datetimes (no trailing Z or offset). Treat any
// such string as UTC so relative-time math doesn't drift by the viewer's offset.
function asUtc(iso: string): string {
  return /Z$|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`;
}

export function formatTimeAgo(iso: string | null | undefined): string {
  if (!iso) return '—';

  return `${formatDistanceToNowStrict(new Date(iso))} ago`;
}

export function formatAbsoluteLocal(iso: string | null | undefined): string {
  if (!iso) return '—';

  return new Date(asUtc(iso)).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  });
}

export function formatLocalShort(iso: string | null | undefined): string {
  if (!iso) return '—';

  const date = new Date(asUtc(iso));
  const datePart = date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
  const timePart = date.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  });
  return `${datePart}, ${timePart}`;
}
