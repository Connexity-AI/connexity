'use client';

import { useEffect, useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Check, ChevronsUpDown, Plus } from 'lucide-react';
import { useTheme } from 'next-themes';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';
import { cn } from '@workspace/ui/lib/utils';

import { logoutAction } from '@/actions/auth';
import { openWorkspaceAction } from '@/actions/workspaces';
import { NewWorkspaceDialog } from '@/components/shell/new-workspace-dialog';

import type { WorkspacePublic } from '@/client/types.gen';
import type { FC } from 'react';

/** The list scrolls past six workspaces; search appears past eight. */
const SEARCH_FROM = 9;

const THEMES = [
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
  { value: 'system', label: 'System' },
] as const;

interface Props {
  name: string;
  workspaces: WorkspacePublic[];
}

const ThemePicker: FC = () => {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // The stored theme is only known in the browser.
  useEffect(() => setMounted(true), []);

  return (
    <div className="flex flex-col gap-1.5 px-2.5 py-2">
      <span className="text-label text-ink-secondary">Theme</span>
      <div
        role="radiogroup"
        aria-label="Theme"
        className="flex rounded-md border border-border-control p-0.5"
      >
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

const WorkspaceList: FC<{ workspaces: WorkspacePublic[]; onNew: () => void }> = ({
  workspaces,
  onNew,
}) => {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [isPending, startTransition] = useTransition();

  const q = query.trim().toLowerCase();
  const shown = q ? workspaces.filter((w) => w.name.toLowerCase().includes(q)) : workspaces;

  const open = (workspace: WorkspacePublic) => {
    if (workspace.is_open) return;
    startTransition(async () => {
      await openWorkspaceAction(workspace.id);
      router.push(UrlGenerator.home());
      router.refresh();
    });
  };

  return (
    <>
      <span className="px-2.5 pt-1.5 pb-1 text-label text-ink-muted">Workspaces</span>
      {workspaces.length >= SEARCH_FROM && (
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.stopPropagation()}
          placeholder="Find a workspace"
          aria-label="Find a workspace"
          className="mx-0.5 mt-0.5 mb-1 h-8 rounded-sm border border-border-control bg-surface-1 px-2.5 text-label text-ink outline-none placeholder:text-ink-muted"
        />
      )}
      <div className="flex max-h-60 flex-col overflow-y-auto">
        {shown.map((workspace) => (
          <DropdownMenuItem
            key={workspace.id}
            disabled={isPending}
            onSelect={() => open(workspace)}
            className="flex h-[34px] cursor-pointer items-center gap-2.5 rounded-sm px-2.5 text-label text-ink focus:bg-wash"
          >
            <span className="min-w-0 flex-1 truncate">{workspace.name}</span>
            {workspace.is_open && <Check className="size-3.5 flex-none" aria-label="Open" />}
          </DropdownMenuItem>
        ))}
      </div>
      <DropdownMenuItem
        onSelect={onNew}
        className="flex h-[34px] cursor-pointer items-center gap-2 rounded-sm px-2.5 text-label text-ink-secondary focus:bg-wash focus:text-ink"
      >
        <Plus className="size-3.5" aria-hidden />
        New workspace
      </DropdownMenuItem>
    </>
  );
};

export const ProfileMenu: FC<Props> = ({ name, workspaces }) => {
  const [isPending, startTransition] = useTransition();
  const [dialogOpen, setDialogOpen] = useState(false);
  const initial = name.trim().charAt(0).toUpperCase();
  const openWorkspace = workspaces.find((w) => w.is_open);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          title="Workspaces, account and theme"
          className="flex min-h-11 w-full cursor-pointer items-center gap-2.5 rounded-md px-3 py-1 text-left outline-none hover:bg-wash focus-visible:bg-wash"
        >
          <span
            aria-hidden
            className="flex size-6 flex-none items-center justify-center rounded-full bg-unchecked-bg text-xs font-medium text-ink-secondary"
          >
            {initial}
          </span>
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-label text-ink">{name}</span>
            {openWorkspace && (
              <span className="truncate text-label text-ink-muted">{openWorkspace.name}</span>
            )}
          </span>
          <ChevronsUpDown className="size-3.5 flex-none text-ink-muted" aria-hidden />
        </DropdownMenuTrigger>

        <DropdownMenuContent
          side="top"
          align="start"
          sideOffset={6}
          className="flex w-(--radix-dropdown-menu-trigger-width) flex-col rounded-md border-hairline bg-surface-2 p-1 text-ink shadow-menu"
        >
          <WorkspaceList workspaces={workspaces} onNew={() => setDialogOpen(true)} />
          <DropdownMenuSeparator className="mx-0 my-1 bg-hairline" />
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
      <NewWorkspaceDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </>
  );
};

export default ProfileMenu;
