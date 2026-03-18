import { redirect } from 'next/navigation';

import { SidebarProvider } from '@workspace/ui/components/ui/sidebar';

import Header from '@/components/dashboard/layout/header';
import Sidebar from '@/components/dashboard/layout/sidebar';
import { UsersService } from '@/client/sdk.gen';
import { ROUTES } from '@/constants/routes';

import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

const { LOGIN } = ROUTES;

const DashboardLayout: FC<Props> = async ({ children }) => {
  const result = await UsersService.readUserMe();
  const currentUser = result.data;

  if (result.error || !currentUser) redirect(LOGIN);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <Sidebar currentUser={currentUser} />
        <div className="flex-1 flex flex-col">
          <Header />
          <main className="flex-1 p-6 bg-slate-50 dark:bg-slate-900">{children}</main>
        </div>
      </div>
    </SidebarProvider>
  );
};

export default DashboardLayout;
