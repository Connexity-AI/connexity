import { formatDistanceToNowStrict } from 'date-fns';

function asUtc(iso: string): string {
  return iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`;
}

export function formatTimeAgo(iso: string | null | undefined): string {
  if (!iso) return '—';

  return `${formatDistanceToNowStrict(new Date(asUtc(iso)))} ago`;
}
