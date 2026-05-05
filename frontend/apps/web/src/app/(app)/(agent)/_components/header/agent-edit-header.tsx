'use client';

import { useParams, useSelectedLayoutSegment } from 'next/navigation';

import { cn } from '@workspace/ui/lib/utils';

import { AgentEditActions } from '@/app/(app)/(agent)/_components/header/agent-edit-actions';
import { AgentEditBreadcrumb } from '@/app/(app)/(agent)/_components/header/agent-edit-breadcrumb';
import {
  AgentModeTabs,
  type AgentPageMode,
} from '@/app/(app)/(agent)/_components/header/agent-mode-tabs';

const HEADER_CLASSNAME = cn(
  'relative h-16 border-b border-border flex items-center justify-center sticky top-0 z-10',
  'bg-card dark:bg-zinc-900 px-6'
);

export function AgentEditHeader() {
  const { agentId } = useParams<{ agentId: string }>();
  const segment = useSelectedLayoutSegment() as AgentPageMode | null;
  const activeMode: AgentPageMode = segment ?? 'edit';

  return (
    <header className={HEADER_CLASSNAME}>
      <div className="absolute inset-y-0 left-6 flex items-center">
        <AgentEditBreadcrumb />
      </div>

      <AgentModeTabs agentId={agentId} activeMode={activeMode} />

      {activeMode === 'edit' && (
        <div className="absolute inset-y-0 right-6 flex items-center">
          <AgentEditActions />
        </div>
      )}
    </header>
  );
}
