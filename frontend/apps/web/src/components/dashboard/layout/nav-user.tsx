'use client';

import { useTransition } from 'react';

import { ChevronUp, LogOut, Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';

import { Button } from '@workspace/ui/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';

import { logoutAction } from '@/actions/auth';

import type { FC } from 'react';

interface Props {
  email: string;
}

const NavUser: FC<Props> = ({ email }) => {
  const [isPending, startTransition] = useTransition();
  const { theme, setTheme } = useTheme();

  const handleLogout = () => startTransition(() => logoutAction());

  const initials = (email.split('@')[0] ?? '').slice(0, 2).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="h-10 w-full flex items-center gap-3 rounded-lg border border-border px-1 transition-all duration-200 overflow-hidden hover:bg-sidebar-accent/50 hover:border-foreground/20 group-data-[collapsible=icon]:w-10 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:gap-0 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:rounded-full"
        >
          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium text-muted-foreground shrink-0">
            {initials}
          </div>

          <div className="flex-1 min-w-0 text-left group-data-[collapsible=icon]:hidden">
            <p className="text-sm truncate">{email}</p>
          </div>

          <ChevronUp className="w-3.5 h-3.5 text-muted-foreground shrink-0 group-data-[collapsible=icon]:hidden" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        side="top"
        align="start"
        sideOffset={4}
        className="min-w-(--radix-dropdown-menu-trigger-width)"
      >
        <DropdownMenuItem onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
          <Sun className="mr-2 h-4 w-4 dark:hidden" />
          <Moon className="mr-2 h-4 w-4 hidden dark:block" />
          <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} disabled={isPending}>
          <LogOut className="mr-2 h-4 w-4" />
          <span>{isPending ? 'Logging out...' : 'Logout'}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default NavUser;
