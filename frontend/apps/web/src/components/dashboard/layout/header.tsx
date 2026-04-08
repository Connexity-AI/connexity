'use client';

import { SidebarTrigger } from '@workspace/ui/components/ui/sidebar';

import type { FC } from 'react';

const Header: FC = () => {
  return (
    <header className="flex h-16 items-center border-b bg-card dark:bg-zinc-900 px-6">
      <SidebarTrigger />
    </header>
  );
};

export default Header;
