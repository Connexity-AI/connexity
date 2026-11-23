'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { Check, ChevronDown, Ellipsis } from 'lucide-react';

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
  cancelInviteAction,
  invitePeopleAction,
  removeMemberAction,
  resendInviteAction,
  updateMemberAction,
} from '@/actions/agency';

import type { AgencyActionResult } from '@/actions/agency';
import type {
  AgencyDetail,
  AgencyMemberPublic,
  AgencyMemberUpdate,
  AgencyRole,
  AgencyWorkspace,
} from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

const LAST_ADMIN = 'An agency needs at least one Admin.';
const ROLES: { value: AgencyRole; label: string; text: string }[] = [
  { value: 'admin', label: 'Admin', text: 'Manages people and billing' },
  { value: 'member', label: 'Member', text: 'Works in their workspaces' },
];
const roleLabel = (role: AgencyRole) => (role === 'admin' ? 'Admin' : 'Member');
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
const GRID = 'md:grid md:grid-cols-[minmax(0,1fr)_128px_180px_140px_32px] md:items-center md:gap-4';
const MENU =
  'z-20 flex w-60 flex-col rounded-md border-hairline bg-surface-2 p-1 text-ink shadow-menu';
const MENU_ITEM =
  'flex cursor-pointer items-center gap-2.5 rounded-sm px-2.5 text-label text-ink focus:bg-wash';
const TRIGGER =
  'flex h-8 cursor-pointer items-center gap-1 rounded-md border-0 bg-transparent pr-1.5 pl-2 text-label whitespace-nowrap text-ink outline-none hover:bg-wash focus-visible:bg-wash';

/** "All workspaces", one workspace's name, "3 workspaces" or "No workspaces". */
const workspacesLabel = (all: boolean, ids: string[], workspaces: AgencyWorkspace[]): string => {
  if (all) return 'All workspaces';
  if (ids.length === 0) return 'No workspaces';
  if (ids.length === 1) return workspaces.find((w) => w.id === ids[0])?.name ?? '1 workspace';
  return `${ids.length} workspaces`;
};

const Box: FC<{ on: boolean }> = ({ on }) => (
  <span
    aria-hidden
    className={cn(
      'flex size-4 flex-none items-center justify-center rounded-[4px]',
      on ? 'bg-ink text-surface-0' : 'border border-border-control'
    )}
  >
    {on && <Check className="size-3" />}
  </span>
);

interface RolePickerProps {
  role: AgencyRole;
  onPick: (role: AgencyRole) => void;
  bordered?: boolean;
}

const RolePicker: FC<RolePickerProps> = ({ role, onPick, bordered }) => (
  <DropdownMenu>
    <DropdownMenuTrigger
      className={cn(TRIGGER, bordered ? 'border border-border-control pl-2.5' : '-ml-2')}
    >
      {roleLabel(role)}
      <ChevronDown className="size-3.5 text-ink-muted" aria-hidden />
    </DropdownMenuTrigger>
    <DropdownMenuContent align="start" sideOffset={4} className={MENU}>
      {ROLES.map((option) => (
        <DropdownMenuItem
          key={option.value}
          onSelect={() => onPick(option.value)}
          className={cn(MENU_ITEM, 'items-start py-[7px]')}
        >
          <span className="flex h-[18px] w-3.5 flex-none items-center">
            {option.value === role && <Check className="size-3.5" aria-label="Selected" />}
          </span>
          <span className="flex flex-col">
            <span>{option.label}</span>
            <span className="text-ink-muted">{option.text}</span>
          </span>
        </DropdownMenuItem>
      ))}
    </DropdownMenuContent>
  </DropdownMenu>
);

interface WorkspacePickerProps {
  all: boolean;
  ids: string[];
  workspaces: AgencyWorkspace[];
  /** Whether "no workspaces at all" may be chosen (not for an invite). */
  allowNone: boolean;
  onChange: (all: boolean, ids: string[]) => void;
  bordered?: boolean;
}

const WorkspacePicker: FC<WorkspacePickerProps> = ({
  all,
  ids,
  workspaces,
  allowNone,
  onChange,
  bordered,
}) => {
  const toggle = (id: string) => {
    const current = all ? workspaces.map((w) => w.id) : ids;
    const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
    if (next.length === 0 && !allowNone) return;
    onChange(false, next);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          TRIGGER,
          bordered ? 'border border-border-control pl-2.5' : '-ml-2',
          !all && ids.length === 0 && 'text-warning'
        )}
      >
        {workspacesLabel(all, ids, workspaces)}
        <ChevronDown className="size-3.5 text-ink-muted" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" sideOffset={4} className={MENU}>
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            onChange(true, []);
          }}
          className={cn(MENU_ITEM, 'h-[34px]')}
        >
          <Box on={all} />
          All workspaces
        </DropdownMenuItem>
        {workspaces.map((workspace) => (
          <DropdownMenuItem
            key={workspace.id}
            onSelect={(e) => {
              e.preventDefault();
              toggle(workspace.id);
            }}
            className={cn(MENU_ITEM, 'h-[34px]')}
          >
            <Box on={all || ids.includes(workspace.id)} />
            <span className="truncate">{workspace.name}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

const ApproveBox: FC<{ can: boolean; onChange: (can: boolean) => void }> = ({ can, onChange }) => (
  <button
    type="button"
    role="checkbox"
    aria-checked={can}
    onClick={() => onChange(!can)}
    className="flex cursor-pointer items-center gap-2 border-0 bg-transparent p-0 text-label text-ink"
  >
    <Box on={can} />
    {can ? 'Can approve' : 'View only'}
  </button>
);

const Person: FC<{ name: string; second: string; chip?: ReactNode }> = ({ name, second, chip }) => (
  <span className="flex min-w-0 items-center gap-2.5">
    <span
      aria-hidden
      className="flex size-6 flex-none items-center justify-center rounded-full bg-unchecked-bg text-label font-medium text-ink-secondary"
    >
      {name.charAt(0).toUpperCase()}
    </span>
    <span className="flex min-w-0 flex-col">
      <span className="flex min-w-0 items-center gap-2">
        <span className="truncate">{name}</span>
        {chip}
      </span>
      <span className="truncate text-label text-ink-muted">{second}</span>
    </span>
  </span>
);

const daysLeft = (expiresAt: string): string => {
  const days = Math.max(1, Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 86_400_000));
  return `Expires in ${plural(days, 'day', 'days')}`;
};

interface Props {
  agency: AgencyDetail;
}

/**
 * Agency settings › Members (designs/screens/Connexity Agency Members.dc.html). An
 * Admin edits, invites and removes; a Member sees the same table read only.
 */
export const MembersView: FC<Props> = ({ agency }) => {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [failure, setFailure] = useState<string | null>(null);
  const [removing, setRemoving] = useState<AgencyMemberPublic | null>(null);
  const isAdmin = agency.role === 'admin';
  const admins = agency.members.filter((m) => m.role === 'admin').length;

  const run = (action: () => Promise<AgencyActionResult>, after?: () => void) => {
    setFailure(null);
    startTransition(async () => {
      const result = await action();
      if (!result.ok) return setFailure(result.message);
      after?.();
      router.refresh();
    });
  };
  const change = (member: AgencyMemberPublic, body: AgencyMemberUpdate) =>
    run(() => updateMemberAction(agency.id, member.user_id, body));

  const count =
    plural(agency.members.length, 'person', 'people') +
    (agency.invites.length ? ` · ${agency.invites.length} invited` : '');

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="flex flex-col gap-2">
        <span className="text-label text-ink-secondary">{count}</span>
        <div className="rounded-xl border border-hairline bg-surface-1">
          <div className={cn(GRID, 'hidden h-10 pr-4 pl-6 text-label text-ink-secondary md:grid')}>
            <span>Person</span>
            <span>Role</span>
            <span>Workspaces</span>
            <span>Can approve</span>
            <span />
          </div>

          {agency.members.map((member) => {
            const lastAdmin = member.role === 'admin' && admins === 1;
            return (
              <div
                key={member.user_id}
                className={cn(
                  GRID,
                  'flex flex-col gap-2 border-t border-hairline py-3 pr-4 pl-6 md:min-h-14 md:py-0'
                )}
              >
                <Person
                  name={member.full_name || member.email}
                  second={member.email}
                  chip={
                    member.is_you && (
                      <span className="flex h-5 flex-none items-center rounded-sm border border-hairline px-1.5 text-label text-ink-secondary">
                        You
                      </span>
                    )
                  }
                />
                {isAdmin ? (
                  <>
                    {lastAdmin ? (
                      <span
                        title={LAST_ADMIN}
                        aria-disabled
                        className="flex h-8 cursor-default items-center gap-1 text-label text-ink-muted"
                      >
                        {roleLabel(member.role)}
                        <ChevronDown className="size-3.5" aria-hidden />
                      </span>
                    ) : (
                      <span>
                        <RolePicker
                          role={member.role}
                          onPick={(role) => role !== member.role && change(member, { role })}
                        />
                      </span>
                    )}
                    <span>
                      <WorkspacePicker
                        all={member.all_workspaces}
                        ids={member.workspace_ids}
                        workspaces={agency.workspaces}
                        allowNone
                        onChange={(all, ids) =>
                          change(member, { all_workspaces: all, workspace_ids: ids })
                        }
                      />
                    </span>
                    <ApproveBox
                      can={member.can_approve}
                      onChange={(can) => change(member, { can_approve: can })}
                    />
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        aria-label={`More for ${member.full_name || member.email}`}
                        className="flex size-8 cursor-pointer items-center justify-center rounded-md border-0 bg-transparent p-0 text-ink-muted outline-none hover:bg-wash hover:text-ink"
                      >
                        <Ellipsis className="size-4" aria-hidden />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent
                        align="end"
                        sideOffset={4}
                        className={cn(MENU, 'w-[200px]')}
                      >
                        {lastAdmin ? (
                          <DropdownMenuItem
                            disabled
                            title={LAST_ADMIN}
                            className={cn(MENU_ITEM, 'h-[34px] text-ink-muted')}
                          >
                            Remove from agency
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem
                            onSelect={() => setRemoving(member)}
                            className={cn(MENU_ITEM, 'h-[34px] text-critical')}
                          >
                            Remove from agency
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </>
                ) : (
                  <>
                    <span className="text-label text-ink-secondary">{roleLabel(member.role)}</span>
                    <span
                      className={cn(
                        'text-label',
                        !member.all_workspaces && member.workspace_ids.length === 0
                          ? 'text-warning'
                          : 'text-ink-secondary'
                      )}
                    >
                      {workspacesLabel(
                        member.all_workspaces,
                        member.workspace_ids,
                        agency.workspaces
                      )}
                    </span>
                    <span className="text-label text-ink-secondary">
                      {member.can_approve ? 'Can approve' : 'View only'}
                    </span>
                    <span />
                  </>
                )}
              </div>
            );
          })}

          {agency.invites.map((invite) => (
            <div
              key={invite.id}
              className={cn(
                GRID,
                'flex flex-col gap-2 border-t border-hairline py-3 pr-4 pl-6 md:min-h-14 md:py-0'
              )}
            >
              <Person
                name={invite.email}
                second={daysLeft(invite.expires_at)}
                chip={
                  <span className="flex h-5 flex-none items-center rounded-sm bg-unchecked-bg px-1.5 text-label text-ink-secondary">
                    Invited
                  </span>
                }
              />
              <span className="text-label text-ink-secondary">{roleLabel(invite.role)}</span>
              <span className="text-label text-ink-secondary">
                {workspacesLabel(invite.all_workspaces, invite.workspace_ids, agency.workspaces)}
              </span>
              <span className="text-label text-ink-secondary">
                {invite.can_approve ? 'Can approve' : 'View only'}
              </span>
              <DropdownMenu>
                <DropdownMenuTrigger
                  aria-label={`More for ${invite.email}`}
                  className="flex size-8 cursor-pointer items-center justify-center rounded-md border-0 bg-transparent p-0 text-ink-muted outline-none hover:bg-wash hover:text-ink"
                >
                  <Ellipsis className="size-4" aria-hidden />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" sideOffset={4} className={cn(MENU, 'w-[200px]')}>
                  <DropdownMenuItem
                    onSelect={() => run(() => resendInviteAction(agency.id, invite.id))}
                    className={cn(MENU_ITEM, 'h-[34px]')}
                  >
                    Resend invite
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onSelect={() => run(() => cancelInviteAction(agency.id, invite.id))}
                    className={cn(MENU_ITEM, 'h-[34px]')}
                  >
                    Cancel invite
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))}

          <div className="border-t border-hairline px-6 pt-3 pb-4 text-label text-ink-muted">
            People who can approve may archive issues, close incidents, override the gate, and
            change the Playbook and checks, in the workspaces they can access.
          </div>
        </div>
        {failure && (
          <span role="alert" className="text-label text-critical">
            {failure}
          </span>
        )}
      </div>

      {isAdmin && <InviteRow agency={agency} disabled={isPending} />}

      <RemoveDialog
        member={removing}
        onClose={() => setRemoving(null)}
        onRemove={(member) =>
          run(
            () => removeMemberAction(agency.id, member.user_id),
            () => setRemoving(null)
          )
        }
        busy={isPending}
      />
    </div>
  );
};

const InviteRow: FC<{ agency: AgencyDetail; disabled: boolean }> = ({ agency, disabled }) => {
  const router = useRouter();
  const [emails, setEmails] = useState('');
  const [role, setRole] = useState<AgencyRole>('member');
  const [all, setAll] = useState(true);
  const [ids, setIds] = useState<string[]>([]);
  const [can, setCan] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);
  const [sent, setSent] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const send = () => {
    const list = emails
      .split(/[,\s]+/)
      .map((e) => e.trim())
      .filter(Boolean);
    if (list.length === 0 || isPending) return;
    setProblems([]);
    setSent(null);
    startTransition(async () => {
      const answer = await invitePeopleAction(agency.id, {
        emails: list,
        role,
        all_workspaces: all,
        workspace_ids: all ? [] : ids,
        can_approve: can,
      });
      if (!answer.ok) return setProblems([answer.message]);
      const { sent: invited, refused } = answer.result;
      setProblems(refused.map((r) => r.message));
      if (invited.length) setSent(`Invite sent to ${invited.map((i) => i.email).join(', ')}`);
      // Keep what could not be invited in the field, to be corrected.
      setEmails(refused.map((r) => r.email).join(', '));
      router.refresh();
    });
  };

  return (
    <div className="flex flex-col gap-2.5 rounded-xl border border-hairline bg-surface-1 px-6 py-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex-none font-medium text-ink">Invite</span>
        <input
          value={emails}
          onChange={(e) => {
            setEmails(e.target.value);
            setProblems([]);
          }}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Emails, separated by commas"
          aria-label="Emails to invite"
          aria-invalid={problems.length > 0 || undefined}
          className={cn(
            'h-8 min-w-[220px] flex-1 rounded-md border bg-surface-0 px-2.5 text-label text-ink outline-none placeholder:text-ink-muted focus-visible:ring-2 focus-visible:ring-border-control',
            problems.length ? 'border-critical' : 'border-border-control'
          )}
        />
        <RolePicker role={role} onPick={setRole} bordered />
        <WorkspacePicker
          all={all}
          ids={ids}
          workspaces={agency.workspaces}
          allowNone={false}
          onChange={(nextAll, nextIds) => {
            setAll(nextAll);
            setIds(nextIds);
          }}
          bordered
        />
        <ApproveBox can={can} onChange={setCan} />
        <Button onClick={send} disabled={disabled || isPending} className="h-8 px-3.5">
          Invite
        </Button>
      </div>
      {problems.map((problem) => (
        <span key={problem} role="alert" className="text-label text-critical">
          {problem}
        </span>
      ))}
      {sent && <span className="text-label text-ink-secondary">{sent}</span>}
    </div>
  );
};

interface RemoveDialogProps {
  member: AgencyMemberPublic | null;
  onClose: () => void;
  onRemove: (member: AgencyMemberPublic) => void;
  busy: boolean;
}

const RemoveDialog: FC<RemoveDialogProps> = ({ member, onClose, onRemove, busy }) => {
  const name = member?.full_name || member?.email || '';
  const first = name.split(' ')[0];
  const reach = member?.workspace_ids.length ?? 0;
  const assistants = member?.assistants ?? 0;

  return (
    <Dialog open={member !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogTitle>Remove {name}?</DialogTitle>
        <DialogDescription className="text-body text-ink-secondary">
          {first} loses access to {reach === 1 ? 'their workspace' : `all ${reach} workspaces`}{' '}
          right away.
          {assistants > 0 &&
            ` ${first}’s ${plural(assistants, 'connected assistant stops', 'connected assistants stop')} reaching them too.`}{' '}
          What {first} did stays on record.
        </DialogDescription>
        <div className="flex justify-end gap-2">
          <DialogClose asChild>
            <Button type="button" variant="secondary" className="px-3.5">
              Cancel
            </Button>
          </DialogClose>
          <Button
            type="button"
            disabled={busy}
            onClick={() => member && onRemove(member)}
            className="bg-critical text-surface-0 hover:opacity-90"
          >
            Remove
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MembersView;
