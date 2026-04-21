'use client';

import { Loader2, Trash2 } from 'lucide-react';

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
import { cn } from '@workspace/ui/lib/utils';

import type { TestCasePublic } from '@/client/types.gen';

interface DeleteTestCasesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testCases: TestCasePublic[];
  onConfirm: () => void;
  isPending: boolean;
}

const MAX_PREVIEW = 4;

export function DeleteTestCasesDialog({
  open,
  onOpenChange,
  testCases,
  onConfirm,
  isPending,
}: DeleteTestCasesDialogProps) {
  const count = testCases.length;
  const preview = testCases.slice(0, MAX_PREVIEW);
  const remaining = Math.max(0, count - MAX_PREVIEW);

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-sm p-0 gap-0 overflow-hidden">
        <AlertDialogHeader className="flex-row items-start gap-3 space-y-0 px-5 pt-5 pb-4">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-500/15">
            <Trash2 className="h-4 w-4 text-red-400" />
          </div>
          <div className="min-w-0 text-left">
            <AlertDialogTitle className="text-sm font-normal text-foreground">
              Delete {count} test case{count !== 1 ? 's' : ''}?
            </AlertDialogTitle>
            <AlertDialogDescription className="mt-1 text-xs leading-relaxed">
              This will permanently remove the selected test cases. This action cannot be undone.
            </AlertDialogDescription>
          </div>
        </AlertDialogHeader>

        {preview.length > 0 && (
          <div className="mx-5 mb-4 overflow-hidden rounded-lg border border-border bg-accent/20">
            {preview.map((item, index) => (
              <div
                key={item.id}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 text-xs',
                  index > 0 && 'border-t border-border/50'
                )}
              >
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red-400/60" />
                <span className="truncate text-muted-foreground">{item.name}</span>
              </div>
            ))}
            {remaining > 0 && (
              <div className="border-t border-border/50 px-3 py-2 text-[10px] italic text-muted-foreground/50">
                + {remaining} more…
              </div>
            )}
          </div>
        )}

        <AlertDialogFooter className="flex items-center gap-2 px-5 pb-5">
          <AlertDialogCancel className="h-8 text-xs" disabled={isPending}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            className="h-8 gap-1.5 border-0 bg-red-500 text-xs text-white hover:bg-red-600"
            disabled={isPending}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
            Delete {count} test case{count !== 1 ? 's' : ''}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
