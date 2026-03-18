import Image from 'next/image';
import Link from 'next/link';

import { Home, Settings } from 'lucide-react';

import {
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  Sidebar as UISidebar,
} from '@workspace/ui/components/ui/sidebar';

import WithIsActive from '@/components/dashboard/layout/with-is-active';
import { ROUTES } from '@/constants/routes';

import type { UserPublic } from '@/client/types.gen';
import type { FC } from 'react';

import fastApiLogo from '@/assets/images/fastapi-logo.svg';

const { DASHBOARD, SETTINGS } = ROUTES;

interface Props {
  currentUser: UserPublic;
}

const menuItems = [
  {
    title: 'Dashboard',
    url: DASHBOARD,
    icon: Home,
  },
  {
    title: 'User Settings',
    url: SETTINGS,
    icon: Settings,
  },
] as const;

const Sidebar: FC<Props> = async ({ currentUser }) => {
  return (
    <UISidebar className="border-r bg-white dark:bg-slate-900">
      <SidebarHeader className="p-6">
        <Link href={DASHBOARD} className="flex items-center space-x-3">
          <Image
            src={fastApiLogo}
            alt="FastAPI Logo"
            width={500}
            height={500}
            className="w-40 h-8 object-contain"
          />
        </Link>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  {/* passes isActive prop */}
                  <WithIsActive url={item.url}>
                    <SidebarMenuButton
                      asChild
                      className="text-gray-700 dark:text-gray-300 hover:text-slate-900 hover:bg-gray-100 dark:hover:text-white dark:hover:bg-slate-800 data-[state=open]:bg-gray-100 dark:data-[state=open]:bg-slate-800"
                    >
                      <Link href={item.url} className="flex items-center gap-2">
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </WithIsActive>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-6">
        {currentUser.email && (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            <p>Logged in as:</p>
            <p className="font-medium">{currentUser.email}</p>
          </div>
        )}
      </SidebarFooter>
    </UISidebar>
  );
};

export default Sidebar;
