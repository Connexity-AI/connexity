'use client';

import type { ReactNode } from 'react';

import type { MetricTier } from '@/client/types.gen';

function Root({ children }: { children: ReactNode }) {
  return <div className="overflow-hidden rounded-lg border border-border">{children}</div>;
}

function Header({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border bg-accent/10 px-5 py-3">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60">{title}</p>
      {action}
    </div>
  );
}

function Body({ children }: { children: ReactNode }) {
  return <div className="px-5 py-4">{children}</div>;
}

export const Section = Object.assign(Root, { Header, Body });

export function FieldLabel({ children }: { children: ReactNode }) {
  return (
    <label className="mb-1.5 block text-xs text-muted-foreground">{children}</label>
  );
}

export function FieldHint({ children }: { children: ReactNode }) {
  return <p className="mt-1 text-[10px] text-muted-foreground/40">{children}</p>;
}

export const EVAL_TIER_DOT: Record<MetricTier, string> = {
  execution: 'bg-blue-500',
  knowledge: 'bg-purple-500',
  process: 'bg-amber-500',
  delivery: 'bg-emerald-500',
};
