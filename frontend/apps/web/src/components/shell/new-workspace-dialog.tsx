'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import { cn } from '@workspace/ui/lib/utils';

import { createWorkspaceAction } from '@/actions/workspaces';
import { isErrorApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { FC, FormEvent } from 'react';

const NAME_MAX_LENGTH = 255;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** New workspace (designs/screens/Connexity Sidebar.dc.html): creates and opens it. */
export const NewWorkspaceDialog: FC<Props> = ({ open, onOpenChange }) => {
  const router = useRouter();
  const [name, setName] = useState('');
  const [failure, setFailure] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const tooLong = name.length > NAME_MAX_LENGTH;
  const canCreate = name.trim().length > 0 && !tooLong && !isPending;

  const change = (next: boolean) => {
    if (!next) {
      setName('');
      setFailure(null);
    }
    onOpenChange(next);
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!canCreate) return;
    startTransition(async () => {
      const result = await createWorkspaceAction(name.trim());
      if (isErrorApiResult(result)) return setFailure(getApiErrorMessage(result.error));
      change(false);
      router.push(UrlGenerator.home());
      router.refresh();
    });
  };

  return (
    <Dialog open={open} onOpenChange={change}>
      <DialogContent aria-describedby={undefined}>
        <DialogTitle>New workspace</DialogTitle>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
          <label className="flex flex-col gap-1.5">
            <span className="text-label text-ink-secondary">Name</span>
            <input
              autoFocus
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setFailure(null);
              }}
              aria-invalid={tooLong || undefined}
              className={cn(
                'h-9 rounded-md border bg-surface-0 px-3 text-body text-ink outline-none focus-visible:ring-2 focus-visible:ring-border-control',
                tooLong ? 'border-critical' : 'border-border-control'
              )}
            />
            {tooLong ? (
              <span className="text-label text-critical">Use 255 characters or fewer.</span>
            ) : (
              <DialogDescription className="text-label text-ink-muted">
                Usually the client’s name
              </DialogDescription>
            )}
            {failure && <span className="text-label text-critical">{failure}</span>}
          </label>
          <div className="flex justify-end gap-2">
            <DialogClose asChild>
              <Button type="button" variant="secondary" className="px-3.5">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={!canCreate} className="disabled:opacity-40">
              Create
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default NewWorkspaceDialog;
