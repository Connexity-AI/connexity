'use client';

import { Play, Save } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

interface CreateEvalSaveActionsProps {
  readOnly: boolean;
  isPending: boolean;
  onSave: () => void;
  onSaveAndRun: () => void;
}

export function CreateEvalSaveActions({
  readOnly,
  isPending,
  onSave,
  onSaveAndRun,
}: CreateEvalSaveActionsProps) {
  if (readOnly) return null;

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8 gap-1.5 text-xs"
        onClick={onSave}
        disabled={isPending}
      >
        <Save className="h-3.5 w-3.5" />
        Save
      </Button>

      <Button
        type="button"
        size="sm"
        className="h-8 gap-1.5 text-xs"
        onClick={onSaveAndRun}
        disabled={isPending}
      >
        <Play className="h-3.5 w-3.5" />
        Save &amp; Run
      </Button>
    </>
  );
}
