'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { openWorkspaceAction } from '@/actions/workspaces';
import { Brand } from '@/components/common/brand';

import type { FC } from 'react';

interface Props {
  /** A workspace the person still reaches. */
  workspace: { id: string; name: string };
}

/**
 * What a person sees when the workspace their session was opened in has been deleted
 * (designs/screens/Connexity Workspace Deleting.dc.html). The link opens another
 * workspace, which gives them a session there.
 */
export const WorkspaceDeleted: FC<Props> = ({ workspace }) => {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const go = () =>
    startTransition(async () => {
      await openWorkspaceAction(workspace.id);
      router.push(UrlGenerator.home());
      router.refresh();
    });

  return (
    <div className="flex min-h-screen w-full flex-col bg-surface-0 text-ink">
      <div className="flex-none px-8 py-6">
        <Brand />
      </div>
      <main className="flex flex-1 items-center justify-center px-6 pb-32">
        <div role="status" className="flex flex-col items-center gap-2 text-center">
          <p className="m-0 text-heading">This workspace is being deleted.</p>
          <button
            type="button"
            disabled={isPending}
            onClick={go}
            className="cursor-pointer border-0 bg-transparent p-0 text-body text-ink-secondary underline hover:opacity-80"
          >
            Go to {workspace.name}
          </button>
        </div>
      </main>
    </div>
  );
};

export default WorkspaceDeleted;
