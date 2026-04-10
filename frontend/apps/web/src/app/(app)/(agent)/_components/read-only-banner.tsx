'use client';

import { Clock, GitCompare, RotateCcw } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Separator } from '@workspace/ui/components/ui/separator';
import { cn } from '@workspace/ui/lib/utils';

import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useRollbackAgent } from '@/app/(app)/(agent)/_hooks/use-rollback-agent';

export function ReadOnlyBanner() {
  const { selectedVersion, selectVersion, isReadOnly, showDiff, toggleDiff } = useVersions();
  const { agentId } = useAgentEditFormActions();
  const { mutate: rollback, isPending } = useRollbackAgent(agentId);

  if (!isReadOnly || selectedVersion === null) return null;

  const handleRollback = () => {
    rollback(
      { version: selectedVersion, change_description: `Rollback to V${selectedVersion}` },
      {
        onSuccess: () => selectVersion(null),
      }
    );
  };

  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-blue-500/20 bg-blue-500/5 shrink-0">
      <div className="flex items-center gap-2 text-xs text-blue-400">
        <Clock className="w-3.5 h-3.5 shrink-0" />
        <span>Viewing v{selectedVersion}</span>
        <span className="text-blue-400/50">· Read-only</span>
      </div>

      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={toggleDiff}
          className={cn(
            'h-7 px-2.5 gap-1.5 text-xs font-normal rounded [&_svg]:size-3.5!',
            showDiff
              ? 'bg-blue-500/20 border-blue-500/40 text-blue-300 hover:bg-blue-500/20 hover:text-blue-300'
              : 'border-blue-500/20 text-blue-400/70 hover:bg-blue-500/10 hover:text-blue-400'
          )}
        >
          <GitCompare />
          {showDiff ? 'Hide diff' : 'View diff'}
        </Button>

        <Separator orientation="vertical" className="h-4 bg-blue-400/20" />

        <Button
          size="sm"
          variant="link"
          onClick={() => selectVersion(null)}
          className="h-auto p-0 text-xs font-normal text-blue-400/60 hover:text-blue-400 hover:no-underline"
        >
          Back to draft
        </Button>

        <Button
          size="sm"
          variant="outline"
          onClick={handleRollback}
          disabled={isPending}
          className="h-7 px-2.5 gap-1.5 text-xs font-normal border-blue-500/30 text-blue-400 hover:bg-blue-500/10 hover:text-blue-400 [&_svg]:size-3!"
        >
          <RotateCcw />
          {isPending ? 'Rolling back...' : 'Roll back'}
        </Button>
      </div>
    </div>
  );
}
