import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { SidebarProvider } from '@workspace/ui/components/ui/sidebar';

import Sidebar from '@/components/dashboard/layout/sidebar';
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

const AppLayout: FC<Props> = async ({ children }) => {
  const [currentUser, cookieStore] = await Promise.all([getAuthenticatedUser(), cookies()]);

  if (!currentUser) redirect(UrlGenerator.login());

  const defaultOpen = cookieStore.get('sidebar:state')?.value !== 'false';

  return (
    <SidebarProvider defaultOpen={defaultOpen}>
      <div className="flex min-h-screen w-full">
        <Sidebar currentUser={currentUser} />

        <div className="flex-1 flex flex-col">{children}</div>
      </div>
    </SidebarProvider>
  );
};

export default AppLayout;
