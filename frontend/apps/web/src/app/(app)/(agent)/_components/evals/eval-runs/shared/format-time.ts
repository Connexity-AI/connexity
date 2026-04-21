import { formatDistanceToNowStrict } from 'date-fns';

export function formatTimeAgo(iso: string | null | undefined): string {
  if (!iso) return '—';

  return `${formatDistanceToNowStrict(new Date(iso))} ago`;
}
