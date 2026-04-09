'use client';

import { ArrowLeft, RotateCcw } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useRollbackAgent } from '@/app/(app)/(agent)/_hooks/use-rollback-agent';

export function ReadOnlyBanner() {
  const { selectedVersion, selectVersion, isReadOnly } = useVersions();
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
    <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/50">
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">
          Viewing <span className="font-medium text-foreground">Version {selectedVersion}</span>{' '}
          (read-only)
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5"
          onClick={() => selectVersion(null)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Draft
        </Button>

        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={handleRollback}
          disabled={isPending}
        >
          <RotateCcw className="h-3.5 w-3.5" />
          {isPending ? 'Rolling back...' : 'Rollback to this version'}
        </Button>
      </div>
    </div>
  );
}
