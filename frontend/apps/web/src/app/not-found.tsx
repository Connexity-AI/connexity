import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { X } from 'lucide-react';

import { Brand } from '@/components/common/brand';

import type { FC } from 'react';

// The dashes before the break move slowly towards it; never with reduced motion.
const FLOW = '@keyframes cx-flow { to { stroke-dashoffset: -8; } }';

const Dashes: FC<{ moving?: boolean }> = ({ moving = false }) => (
  <svg width="100%" height="2" className="block overflow-visible">
    <line
      x1="0"
      y1="1"
      x2="100%"
      y2="1"
      stroke="var(--color-border-control)"
      strokeWidth="1"
      strokeDasharray="4 4"
      className={moving ? 'animate-[cx-flow_0.45s_linear_infinite] motion-reduce:animate-none' : ''}
    />
  </svg>
);

/** A page that does not exist, as a failed call transfer
 * (designs/screens/Connexity 404.dc.html). No sidebar; one way back, to Work. */
const NotFound: FC = () => (
  <div className="flex min-h-screen w-full flex-col bg-surface-0 text-ink">
    <style>{FLOW}</style>
    <div className="flex-none px-5 py-4 sm:px-8 sm:py-6">
      <Link
        href={UrlGenerator.work()}
        aria-label="Connexity, go to Work"
        className="inline-flex no-underline"
      >
        <Brand />
      </Link>
    </div>
    <main className="flex flex-1 items-center justify-center px-6 pb-24 sm:px-8 sm:pb-32">
      <div className="flex w-full max-w-[440px] flex-col items-center text-center">
        <span className="text-[88px] leading-none font-medium tracking-[-0.03em] tabular-nums sm:text-[128px]">
          404
        </span>
        <h1 className="mt-4 text-title font-medium">Page not found</h1>
        <p className="mt-2 text-body text-pretty text-ink-secondary">
          We tried to transfer you, but the line dropped. This page doesn&apos;t exist.
        </p>
        <div aria-hidden className="mt-10 flex w-full items-center">
          <span className="flex h-8 flex-none items-center rounded-lg border border-border-control px-3 text-label whitespace-nowrap text-ink-secondary">
            You
          </span>
          <span className="flex min-w-4 flex-1 items-center">
            <Dashes moving />
          </span>
          <X className="mx-1.5 size-3 flex-none text-critical" strokeWidth={2.5} />
          <span className="flex min-w-4 flex-1 items-center opacity-40">
            <Dashes />
          </span>
          <span className="flex h-8 flex-none items-center rounded-lg border border-dashed border-border-control px-3 text-label whitespace-nowrap text-ink-muted">
            This page
          </span>
        </div>
        <Link
          href={UrlGenerator.work()}
          className="mt-10 inline-flex h-9 items-center rounded-lg bg-accent-ink px-4 text-body font-medium text-on-accent no-underline hover:opacity-90"
        >
          Back to Work
        </Link>
      </div>
    </main>
  </div>
);

export default NotFound;
