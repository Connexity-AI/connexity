'use client';

import Link from 'next/link';
import { useSelectedLayoutSegment } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Tabs, TabsList, TabsTrigger } from '@workspace/ui/components/ui/tabs';
import { cn } from '@workspace/ui/lib/utils';

import type { Route } from 'next';

type EvalsSegment = 'test-cases' | 'eval-configs' | 'eval-runs';

interface EvalsTab {
  segment: EvalsSegment;
  label: string;
  href: ((agentId: string) => Route) | null;
}

const EVALS_TABS: readonly EvalsTab[] = [
  {
    segment: 'test-cases',
    label: 'Test Cases',
    href: UrlGenerator.agentEvalsTestCases,
  },
  {
    segment: 'eval-configs',
    label: 'Eval Configs',
    href: UrlGenerator.agentEvalsConfigs,
  },
  {
    segment: 'eval-runs',
    label: 'Eval Runs',
    href: UrlGenerator.agentEvalsRuns,
  },
] as const;

const EVALS_SEGMENTS = EVALS_TABS.map((t) => t.segment);

function isEvalsSegment(value: string | null): value is EvalsSegment {
  return value !== null && (EVALS_SEGMENTS as readonly string[]).includes(value);
}

interface EvalsTabsProps {
  agentId: string;
}

export function EvalsTabs({ agentId }: EvalsTabsProps) {
  const segment = useSelectedLayoutSegment();
  const active = isEvalsSegment(segment) ? segment : '';

  return (
    <Tabs value={active}>
      <TabsList className="h-auto w-full justify-start rounded-none bg-transparent p-0 px-4 border-b border-border">
        {EVALS_TABS.map(({ segment, label, href }) => (
          <TabsTrigger
            key={segment}
            value={segment}
            asChild={href !== null}
            disabled={href === null}
            className={triggerClassName}
          >
            {/* remove this check when all tabs have urls */}
            {href !== null ? <Link href={href(agentId)}>{label}</Link> : label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

const triggerClassName = cn(
  'relative cursor-pointer rounded-none bg-transparent px-5 py-3 text-sm font-medium shadow-none',
  'transition-colors duration-150 select-none',
  'after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:rounded-t-full after:transition-all after:duration-150',
  'data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none data-[state=active]:after:bg-foreground',
  'data-[state=inactive]:text-muted-foreground data-[state=inactive]:after:bg-transparent',
  'hover:text-foreground hover:after:bg-border',
  'focus-visible:ring-0 focus-visible:ring-offset-0',
  'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:text-muted-foreground disabled:hover:after:bg-transparent'
);
