'use client';

import { useEffect, useState, useTransition } from 'react';

import { ChevronsUpDown } from 'lucide-react';
import { useTheme } from 'next-themes';

import { cn } from '@workspace/ui/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';

import { logoutAction } from '@/actions/auth';

import type { FC } from 'react';

const THEMES = [
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
  { value: 'system', label: 'System' },
] as const;

interface Props {
  name: string;
}

const ThemePicker: FC = () => {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // The stored theme is only known in the browser.
  useEffect(() => setMounted(true), []);

  return (
    <div className="flex flex-col gap-1.5 px-2.5 py-2">
      <span className="text-label text-ink-secondary">Theme</span>
      <div role="radiogroup" aria-label="Theme" className="flex rounded-md border border-border-control p-0.5">
        {THEMES.map(({ value, label }) => {
          const isOn = mounted && theme === value;
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={isOn}
              onClick={() => setTheme(value)}
              className={cn(
                'h-[26px] flex-1 cursor-pointer rounded-sm px-1.5 text-label',
                isOn ? 'bg-wash font-medium text-ink' : 'text-ink-secondary'
              )}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export const ProfileMenu: FC<Props> = ({ name }) => {
  const [isPending, startTransition] = useTransition();
  const initial = name.trim().charAt(0).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        title="Account and theme"
        className="flex min-h-11 w-full cursor-pointer items-center gap-2.5 rounded-md px-3 py-1 text-left outline-none hover:bg-wash focus-visible:bg-wash"
      >
        <span
          aria-hidden
          className="flex size-6 flex-none items-center justify-center rounded-full bg-unchecked-bg text-xs font-medium text-ink-secondary"
        >
          {initial}
        </span>
        <span className="min-w-0 flex-1 truncate text-label text-ink">{name}</span>
        <ChevronsUpDown className="size-3.5 flex-none text-ink-muted" aria-hidden />
      </DropdownMenuTrigger>

      <DropdownMenuContent
        side="top"
        align="start"
        sideOffset={6}
        className="w-(--radix-dropdown-menu-trigger-width) rounded-md border-hairline bg-surface-2 p-1 text-ink shadow-menu"
      >
        <ThemePicker />
        <DropdownMenuSeparator className="mx-0 my-1 bg-hairline" />
        <DropdownMenuItem
          disabled={isPending}
          onSelect={() => startTransition(() => logoutAction())}
          className="h-9 cursor-pointer rounded-sm px-2.5 text-label text-ink focus:bg-wash"
        >
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default ProfileMenu;
