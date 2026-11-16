import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import type { FC } from 'react';

const R = 6;
const LENGTH = 2 * Math.PI * R;

/**
 * Readiness at the bottom of the sidebar (designs/screens/Connexity Sidebar.dc.html):
 * a small ring and the percentage, until setup is done. It opens Work, where the
 * onboarding steps are rows.
 */
export const ReadinessRing: FC<{ percent: number }> = ({ percent }) => {
  const done = Math.max(0, Math.min(100, percent));
  return (
    <Link
      href={UrlGenerator.work()}
      title="Setup is done on Work"
      className="flex h-9 items-center gap-2.5 rounded-md px-3 text-body text-ink no-underline hover:bg-wash"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" className="flex-none -rotate-90" aria-hidden>
        <circle
          cx="8"
          cy="8"
          r={R}
          fill="none"
          className="stroke-border-control"
          strokeWidth="2"
          opacity="0.45"
        />
        <circle
          cx="8"
          cy="8"
          r={R}
          fill="none"
          className="stroke-ink"
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray={`${(LENGTH * done) / 100} ${LENGTH}`}
        />
      </svg>
      <span className="flex-1">Readiness</span>
      <span className="text-label text-ink-secondary">{done}%</span>
    </Link>
  );
};

export default ReadinessRing;
