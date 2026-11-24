'use client';

import { useState } from 'react';

import { Button } from '@workspace/ui/components/ui/button';

import { NewWorkspaceDialog } from '@/components/shell/new-workspace-dialog';

import type { FC } from 'react';

/**
 * What an Admin sees in place of the app's pages while their agency has no workspace
 * (designs/screens/Connexity Agency.dc.html, "No workspaces yet"). Creating one opens
 * it. Agency settings, Account and Sign out stay in the profile menu.
 */
export const NoWorkspaces: FC = () => {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="flex max-w-sm flex-col items-center gap-5 text-center">
        <div className="flex flex-col gap-1">
          <h1 className="m-0 text-title font-medium text-ink">No workspaces yet</h1>
          <p className="m-0 text-pretty text-body text-ink-secondary">
            Create a workspace for a client to start checking their calls.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} className="h-10 px-4">
          New workspace
        </Button>
      </div>
      <NewWorkspaceDialog open={open} onOpenChange={setOpen} />
    </div>
  );
};

export default NoWorkspaces;
