const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/**
 * Converts an ISO date string into a human-readable relative time label.
 * After {@link absoluteAfterDays} days, falls back to an absolute date (e.g. "3/1/2026").
 *
 * @param dateStr - ISO date string to format
 * @param absoluteAfterDays - Number of days after which to show absolute date (default: 7)
 *
 * @example
 * formatTimeAgo("2026-04-09T12:00:00Z")     // "just now"      (< 1 min)
 * formatTimeAgo("2026-04-09T11:30:00Z")     // "30 mins ago"   (< 1 hour)
 * formatTimeAgo("2026-04-09T03:00:00Z")     // "9 hours ago"   (< 1 day)
 * formatTimeAgo("2026-04-06T12:00:00Z")     // "3 days ago"    (< 7 days)
 * formatTimeAgo("2026-03-01T00:00:00Z")     // "3/1/2026"      (>= 7 days)
 * formatTimeAgo("2026-04-06T12:00:00Z", 2)  // "3/1/2026"      (>= 2 days)
 */
export function formatTimeAgo(dateStr: string, absoluteAfterDays = 7): string {
  const utcStr = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : `${dateStr}Z`;
  const date = new Date(utcStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  if (diff < MINUTE) return 'just now';
  if (diff < HOUR) {
    const mins = Math.floor(diff / MINUTE);
    return `${mins} min${mins === 1 ? '' : 's'} ago`;
  }
  if (diff < DAY) {
    const hours = Math.floor(diff / HOUR);
    return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  }
  if (diff < absoluteAfterDays * DAY) {
    const days = Math.floor(diff / DAY);
    return `${days} day${days === 1 ? '' : 's'} ago`;
  }

  return date.toLocaleDateString('en-US', {
    month: 'numeric',
    day: 'numeric',
    year: 'numeric',
  });
}
