import Image from 'next/image';
import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Bot, Plug } from 'lucide-react';

import {
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  Sidebar as UISidebar,
} from '@workspace/ui/components/ui/sidebar';

import NavUser from '@/components/dashboard/layout/nav-user';
import WithIsActive from '@/components/dashboard/layout/with-is-active';

import type { UserPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  currentUser?: UserPublic;
}

const menuItems = [
  {
    title: 'Agents',
    url: UrlGenerator.agents(),
    icon: Bot,
  },
  {
    title: 'Integrations',
    url: UrlGenerator.integrations(),
    icon: Plug,
  },
];

const Sidebar: FC<Props> = async ({ currentUser }) => {
  return (
    <UISidebar collapsible="icon" className="border-r bg-card dark:bg-zinc-900">
      <SidebarHeader className="border-b px-3 py-4">
        <Link href={UrlGenerator.agents()} className="flex items-center justify-center gap-2 overflow-hidden group-data-[collapsible=icon]:justify-center">
          <Image
            src="/connexity-logo.avif"
            alt="Connexity"
            width={32}
            height={32}
            className="shrink-0 rounded-md"
          />
          <span className="truncate text-lg font-semibold tracking-tight group-data-[collapsible=icon]:hidden">
            Connexity
          </span>
        </Link>
      </SidebarHeader>

      {currentUser && (
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
                        tooltip={item.title}
                        className="text-muted-foreground hover:text-foreground hover:bg-accent dark:hover:bg-zinc-800 data-[state=open]:bg-accent dark:data-[state=open]:bg-zinc-800"
                      >
                        <Link href={item.url} className="flex items-center gap-3">
                          <item.icon className="h-5 w-5" />
                          <span className="text-base">{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </WithIsActive>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
      )}

      {currentUser?.email && (
        <div className="mt-auto p-2 group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
          <NavUser email={currentUser.email} />
        </div>
      )}
    </UISidebar>
  );
};

export default Sidebar;
