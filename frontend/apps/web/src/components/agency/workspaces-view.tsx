'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Ellipsis, TriangleAlert } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';
import { cn } from '@workspace/ui/lib/utils';

import {
  deleteWorkspaceAction,
  previewDeletionAction,
  retryDeletionAction,
} from '@/actions/agency';

import type {
  AgencyWorkspaceRow,
  AgencyWorkspacesTable,
  WorkspaceDeletionPreview,
} from '@/client/types.gen';
import type { FC } from 'react';

const GRID = 'md:grid md:items-center md:gap-4';
const COLS_ADMIN = 'md:grid-cols-[minmax(0,1fr)_88px_120px_120px_32px]';
const COLS_READ = 'md:grid-cols-[minmax(0,1fr)_88px_120px_120px]';
const MENU_ITEM = 'flex h-[34px] items-center rounded-sm px-2.5 text-label';

const number = (n: number) => n.toLocaleString('en-US');
const plural = (n: number, one: string, many: string) => `${number(n)} ${n === 1 ? one : many}`;
const day = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const dayAndTime = (iso: string) =>
  `${day(iso)}, ${new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`;
/** "Retell" from "retell", "n8n" stays as it is. */
const platformName = (key: string) =>
  key === 'n8n' ? key : key.charAt(0).toUpperCase() + key.slice(1);
const listed = (names: string[]) =>
  names.length <= 1 ? (names[0] ?? '') : `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`;

interface Props {
  agencyId: string;
  table: AgencyWorkspacesTable;
}

/**
 * Agency settings › Workspaces (designs/screens/Connexity Workspaces.dc.html): what
 * each workspace holds, and deleting one for good. The server decides who may delete;
 * this only shows the menu to those who can.
 */
export const WorkspacesView: FC<Props> = ({ agencyId, table }) => {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [preview, setPreview] = useState<WorkspaceDeletionPreview | null>(null);
  const [typed, setTyped] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const canDelete = table.can_delete;
  const active = table.workspaces.filter((w) => w.state === null);
  const isLast = active.length <= 1;

  const openDialog = (workspace: AgencyWorkspaceRow) => {
    setFailure(null);
    startTransition(async () => {
      const result = await previewDeletionAction(agencyId, workspace.id);
      if (!result.ok) return setFailure(result.message);
      setTyped('');
      setPreview(result.preview);
    });
  };

  const finish = (name: string, state: string) => {
    setDeletingId(null);
    // After the agency's last workspace there is nothing left to list: the app
    // shows "No workspaces yet".
    if (state === 'done' && isLast) {
      router.push(UrlGenerator.home());
      router.refresh();
      return;
    }
    if (state === 'done') setNote(`${name} was deleted.`);
    router.refresh();
  };

  const confirm = () => {
    if (!preview) return;
    const { workspace_id: id, workspace_name: name } = preview;
    setPreview(null);
    setDeletingId(id);
    setNote(null);
    startTransition(async () => {
      const result = await deleteWorkspaceAction(agencyId, id, typed);
      if (!result.ok) {
        setFailure(result.message);
        setDeletingId(null);
        return;
      }
      finish(name, result.state);
    });
  };

  const retry = (workspace: AgencyWorkspaceRow) => {
    setFailure(null);
    setDeletingId(workspace.id);
    startTransition(async () => {
      const result = await retryDeletionAction(agencyId, workspace.id);
      if (!result.ok) {
        setFailure(result.message);
        setDeletingId(null);
        return;
      }
      finish(workspace.name, result.state);
    });
  };

  const cols = canDelete ? COLS_ADMIN : COLS_READ;

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-col gap-2">
        {note && (
          <span role="status" className="text-label text-ink-secondary">
            {note}
          </span>
        )}
        <div className="rounded-xl border border-hairline bg-surface-1">
          <div
            className={cn(
              GRID,
              cols,
              'hidden h-10 text-label text-ink-secondary md:grid',
              canDelete ? 'pr-4 pl-6' : 'px-6'
            )}
          >
            <span>Workspace</span>
            <span className="text-right">Agents</span>
            <span className="text-right">Calls stored</span>
            <span>Created</span>
            {canDelete && <span />}
          </div>

          {table.workspaces.map((workspace) => {
            const deleting = workspace.id === deletingId || workspace.state === 'deleting';
            const failed = !deleting && workspace.state === 'failed';
            return (
              <div
                key={workspace.id}
                aria-busy={deleting}
                className={cn(
                  GRID,
                  cols,
                  'flex items-center justify-between gap-3 border-t border-hairline py-3 md:min-h-14 md:py-0',
                  canDelete ? 'pr-4 pl-6' : 'px-6'
                )}
              >
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className={cn('truncate text-ink', deleting && 'opacity-50')}>
                    {workspace.name}
                  </span>
                  <span
                    className={cn(
                      'text-label text-ink-secondary tabular-nums md:hidden',
                      deleting && 'opacity-50'
                    )}
                  >
                    {plural(workspace.agents, 'agent', 'agents')} · {number(workspace.calls)} calls
                    · <span suppressHydrationWarning>{day(workspace.created_at)}</span>
                  </span>
                  {deleting && (
                    <span
                      role="status"
                      className="flex items-center gap-2.5 text-label text-ink-secondary"
                    >
                      Deleting…
                      <span
                        aria-hidden
                        className="block h-0.5 w-[120px] flex-none overflow-hidden rounded-full bg-unchecked-bg"
                      >
                        <span className="block h-full w-full animate-pulse rounded-full bg-ink-secondary" />
                      </span>
                    </span>
                  )}
                  {failed && (
                    <span
                      role="alert"
                      className="flex items-start gap-1.5 text-label text-critical"
                    >
                      <TriangleAlert className="mt-0.5 size-3.5 flex-none" aria-hidden />
                      <span>
                        Couldn’t finish deleting.{' '}
                        {canDelete && (
                          <button
                            type="button"
                            disabled={isPending}
                            onClick={() => retry(workspace)}
                            className="cursor-pointer border-0 bg-transparent p-0 font-medium text-critical underline"
                          >
                            Try again
                          </button>
                        )}
                      </span>
                    </span>
                  )}
                </span>
                <span
                  className={cn(
                    'hidden text-right text-ink-secondary tabular-nums md:block',
                    deleting && 'opacity-50'
                  )}
                >
                  {number(workspace.agents)}
                </span>
                <span
                  className={cn(
                    'hidden text-right text-ink-secondary tabular-nums md:block',
                    deleting && 'opacity-50'
                  )}
                >
                  {number(workspace.calls)}
                </span>
                <span
                  suppressHydrationWarning
                  className={cn(
                    'hidden text-label text-ink-secondary md:block',
                    deleting && 'opacity-50'
                  )}
                >
                  {day(workspace.created_at)}
                </span>
                {canDelete && (
                  <span className="flex flex-none justify-end">
                    {workspace.state === null && !deleting && (
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          aria-label={`More for ${workspace.name}`}
                          className="flex size-8 cursor-pointer items-center justify-center rounded-md border-0 bg-transparent p-0 text-ink-muted outline-none hover:bg-wash hover:text-ink"
                        >
                          <Ellipsis className="size-4" aria-hidden />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          align="end"
                          sideOffset={4}
                          className="z-20 flex w-[200px] flex-col overflow-visible rounded-md border-hairline bg-surface-2 p-1 text-ink shadow-menu"
                        >
                          <DropdownMenuItem
                            disabled={isPending}
                            onSelect={() => openDialog(workspace)}
                            className={cn(MENU_ITEM, 'cursor-pointer text-critical focus:bg-wash')}
                          >
                            Delete workspace
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </span>
                )}
              </div>
            );
          })}

          {table.workspaces.length === 0 && (
            <div className="border-t border-hairline px-6 py-4 text-ink-secondary">
              No workspaces yet
            </div>
          )}
          <div className="border-t border-hairline px-6 pt-3 pb-4 text-label text-pretty text-ink-muted">
            Only Admins who can approve can delete a workspace. An assistant can’t delete one: it
            can only send you here.
          </div>
        </div>
        {failure && (
          <span role="alert" className="text-label text-critical">
            {failure}
          </span>
        )}
      </div>

      {table.deleted.length > 0 && (
        <div className="rounded-xl border border-hairline bg-surface-1">
          <div className="flex h-10 items-center px-6 text-label text-ink-secondary">Record</div>
          {table.deleted.map((record) => (
            <div
              key={record.id}
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-0.5 border-t border-hairline px-6 py-3"
            >
              <span className="text-ink">
                {record.deleted_by} deleted {record.workspace_name}
              </span>
              <span suppressHydrationWarning className="text-label text-ink-secondary tabular-nums">
                {dayAndTime(record.finished_at ?? record.created_at)}
              </span>
            </div>
          ))}
          <div className="border-t border-hairline px-6 pt-3 pb-4 text-label text-pretty text-ink-muted">
            Who deleted which workspace, and when. The record holds no call content.
          </div>
        </div>
      )}

      <DeleteDialog
        preview={preview}
        typed={typed}
        onType={setTyped}
        onClose={() => setPreview(null)}
        onDelete={confirm}
      />
    </div>
  );
};

interface DeleteDialogProps {
  preview: WorkspaceDeletionPreview | null;
  typed: string;
  onType: (value: string) => void;
  onClose: () => void;
  onDelete: () => void;
}

const DeleteDialog: FC<DeleteDialogProps> = ({ preview, typed, onType, onClose, onDelete }) => {
  const name = preview?.workspace_name ?? '';
  const matches = name !== '' && typed.trim() === name.trim();
  const connections = (preview?.connections ?? []).map(platformName);
  const lines = preview
    ? [
        [number(preview.calls), 'calls with their recordings and transcripts'],
        [number(preview.agents), 'agents with their specs, scenarios and test runs'],
        [number(preview.issues), 'issues and their history'],
      ]
    : [];

  return (
    <Dialog open={preview !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogTitle>Delete {name}?</DialogTitle>
        <DialogDescription className="text-body text-ink-secondary">
          This permanently deletes the workspace and can’t be undone.
        </DialogDescription>
        <ul className="m-0 flex list-none flex-col gap-1 p-0 text-ink">
          {lines.map(([n, text]) => (
            <li key={text} className="flex gap-2">
              <span className="min-w-12 text-right font-medium tabular-nums">{n}</span>
              <span>{text}</span>
            </li>
          ))}
        </ul>
        <div className="flex flex-col gap-1 text-label text-pretty text-ink-muted">
          {connections.length > 0 && (
            <span>
              Its {listed(connections)}{' '}
              {connections.length === 1 ? 'connection is' : 'connections are'} removed, so no new
              calls arrive. Your calls in {listed(connections)} are not touched.
            </span>
          )}
          <span>Usage totals stay on your invoices, without any call content.</span>
          {preview?.is_last && (
            <span>
              This is your agency’s last workspace. Your subscription keeps running until you cancel
              it.
            </span>
          )}
        </div>
        <label className="flex flex-col gap-1.5 text-label text-ink-secondary">
          <span>
            Type <strong className="font-medium text-ink">{name}</strong> to confirm
          </span>
          <input
            value={typed}
            onChange={(e) => onType(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && matches && onDelete()}
            autoComplete="off"
            spellCheck={false}
            className="h-9 rounded-md border border-border-control bg-surface-0 px-2.5 text-body text-ink outline-none focus-visible:ring-2 focus-visible:ring-border-control"
          />
        </label>
        <div className="flex justify-end gap-2">
          <DialogClose asChild>
            <Button type="button" variant="secondary" className="px-3.5">
              Cancel
            </Button>
          </DialogClose>
          <Button
            type="button"
            disabled={!matches}
            onClick={onDelete}
            className="bg-critical text-surface-0 hover:opacity-90"
          >
            Delete workspace
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default WorkspacesView;
