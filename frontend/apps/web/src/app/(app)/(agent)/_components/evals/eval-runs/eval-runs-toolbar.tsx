'use client';

import { useState } from 'react';
import { Trash2, X } from 'lucide-react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@workspace/ui/components/ui/alert-dialog';
import { Button } from '@workspace/ui/components/ui/button';

import { useDeleteRun } from '@/app/(app)/(agent)/_hooks/use-delete-run';

interface EvalRunsToolbarProps {
  agentId: string;
  totalCount: number;
  filteredCount: number;
  selectedIds: string[];
  onClearSelection: () => void;
}

export function EvalRunsToolbar({
  agentId,
  totalCount,
  filteredCount,
  selectedIds,
  onClearSelection,
}: EvalRunsToolbarProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const deleteRunMutation = useDeleteRun(agentId);

  const handleDelete = async () => {
    for (const id of selectedIds) {
      try {
        await deleteRunMutation.mutateAsync(id);
      } catch (err) {
        console.error('Failed to delete run', id, err);
      }
    }
    setConfirmOpen(false);
    onClearSelection();
  };

  if (selectedIds.length === 0) {
    return (
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-5 py-2.5">
        <p className="text-xs text-muted-foreground">
          {filteredCount === totalCount
            ? `${totalCount} ${totalCount === 1 ? 'run' : 'runs'}`
            : `${filteredCount} of ${totalCount} runs`}
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-5 py-2.5">
        <p className="text-xs text-foreground">
          {selectedIds.length} selected
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearSelection}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <X className="h-3 w-3" />
            Clear
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setConfirmOpen(true)}
            className="h-7 gap-1.5 px-2 text-xs"
          >
            <Trash2 className="h-3 w-3" />
            Delete
          </Button>
        </div>
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {selectedIds.length} {selectedIds.length === 1 ? 'run' : 'runs'}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the selected eval runs and their results.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteRunMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={deleteRunMutation.isPending}
              onClick={(e) => {
                e.preventDefault();
                void handleDelete();
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteRunMutation.isPending ? 'Deleting…' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
