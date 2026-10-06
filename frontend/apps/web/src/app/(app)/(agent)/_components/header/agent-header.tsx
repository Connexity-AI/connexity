'use client';

import { useParams, useSelectedLayoutSegment } from 'next/navigation';

import { cn } from '@workspace/ui/lib/utils';

import { AgentBreadcrumb } from '@/app/(app)/(agent)/_components/header/agent-breadcrumb';
import {
  AgentModeTabs,
  type AgentPageMode,
} from '@/app/(app)/(agent)/_components/header/agent-mode-tabs';

const HEADER_CLASSNAME = cn(
  'relative h-16 border-b border-border flex items-center justify-center sticky top-0 z-10',
  'bg-card dark:bg-zinc-900 px-6'
);

export function AgentHeader() {
  const { agentId } = useParams<{ agentId: string }>();
  const segment = useSelectedLayoutSegment() as AgentPageMode | null;
  const activeMode: AgentPageMode = segment ?? 'observe';

  return (
    <header className={HEADER_CLASSNAME}>
      <div className="absolute inset-y-0 left-6 flex items-center">
        <AgentBreadcrumb agentId={agentId} />
      </div>

      <AgentModeTabs agentId={agentId} activeMode={activeMode} />
    </header>
  );
}
