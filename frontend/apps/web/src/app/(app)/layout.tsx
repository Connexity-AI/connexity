import { redirect } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { listWorkspaces } from '@/actions/workspaces';
import Sidebar from '@/components/shell/sidebar';
import { UsersService } from '@/client/sdk.gen';

import type { UserPublic } from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

async function getAuthenticatedUser(): Promise<UserPublic | undefined> {
  try {
    const result = await UsersService.readUserMe();
    return result.data ?? undefined;
  } catch {
    return undefined;
  }
}

interface Props {
  children: ReactNode;
}

/** The app shell: the sidebar and the page frame beside it. */
const AppLayout: FC<Props> = async ({ children }) => {
  const currentUser = await getAuthenticatedUser();

  if (!currentUser) redirect(UrlGenerator.login());

  const workspaces = await listWorkspaces();

  return (
    <div className="flex min-h-screen w-full bg-surface-0">
      <Sidebar user={currentUser} workspaces={workspaces} />

      <main className="min-w-0 flex-1 px-8 pt-6 pb-12">{children}</main>
    </div>
  );
};

export default AppLayout;
