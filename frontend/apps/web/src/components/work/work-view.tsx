'use client';

import { Fragment, useEffect, useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import {
  ChevronDown,
  ChevronRight,
  CircleCheck,
  CircleHelp,
  FileText,
  Flag,
  FlaskConical,
  GripVertical,
  LoaderCircle,
  Lock,
  Pause,
  Phone,
  RotateCw,
  Siren,
  Wrench,
  X,
} from 'lucide-react';

import { PageBar } from '@workspace/ui/components/page-bar';
import { cn } from '@workspace/ui/lib/utils';

import { moveWorkTaskAction } from '@/actions/work';
import { timeLabel } from '@/components/calls/format';
import { ConnectAssistant } from '@/components/readiness/connect-assistant';
import { QuestionCards } from '@/components/work/question-cards';
import { isErrorApiResult } from '@/utils/api';

import type {
  TaskKind,
  WorkDoneLinkPublic,
  WorkHolderPublic,
  WorkPublic,
  WorkTaskPublic,
  WorkTaskRefPublic,
} from '@/client/types.gen';
import type { LucideIcon } from 'lucide-react';
import type { Route } from 'next';
import type { FC, ReactNode } from 'react';

/** The type icons (designs/16-work.md, "A row"). */
const KIND: Record<TaskKind, { word: string; icon: LucideIcon }> = {
  incident: { word: 'Incident', icon: Siren },
  issue_fix: { word: 'Issue fix', icon: Wrench },
  onboarding: { word: 'Onboarding', icon: Flag },
  spec: { word: 'Spec', icon: FileText },
  clarifications: { word: 'Clarifications', icon: CircleHelp },
  calls_to_review: { word: 'Calls to review', icon: Phone },
  tests: { word: 'Tests', icon: FlaskConical },
};

const STATE_NAME: Record<WorkTaskPublic['state'], string> = {
  in_progress: 'In progress',
  waiting: 'Waiting for you',
  to_do: 'To do',
};

/** "Alex's Claude Code · Onboarding". */
const holderName = (holder: WorkHolderPublic) => {
  const who = `${holder.person}'s ${holder.assistant}`;
  return holder.session ? `${who} · ${holder.session}` : who;
};

/** "The same booking is made twice + 1 more". */
const named = (refs: WorkTaskRefPublic[]) =>
  refs.length > 1 ? `${refs[0]!.title} + ${refs.length - 1} more` : (refs[0]?.title ?? '');

const isBlocked = (task: WorkTaskPublic) =>
  task.state === 'to_do' && (task.blocked_by?.length ?? 0) > 0;

/** A blocked row's lock is warm when what blocks it waits for the person. */
const warmLock = (task: WorkTaskPublic) =>
  (task.blocked_by ?? []).some((ref) => ref.waiting_for_person);

/** Where the person acts on a task that waits for them. */
const action = (task: WorkTaskPublic): { label: string; href: Route } | undefined => {
  if (task.kind === 'clarifications' && task.agent_id) {
    return { label: 'Answer questions →', href: UrlGenerator.work(task.agent_id) };
  }
  return undefined;
};

/** A held task whose session has gone quiet: "No activity since 14:20". */
const quietSince = (task: WorkTaskPublic) => task.holder?.quiet_since ?? null;

/** Where a finished task's work is. */
const doneHref = (link: WorkDoneLinkPublic): Route => {
  if (link.kind === 'issue') return UrlGenerator.issue(link.id);
  const tab = { agent_spec: 'spec', agent_tests: 'tests', agent_calls: 'calls' } as const;
  return UrlGenerator.agentTab(link.id, tab[link.kind]);
};

/** "Updated just now", "Updated 2 min ago". */
const updatedLabel = (at: number, now: number) => {
  const minutes = Math.floor((now - at) / 60_000);
  if (minutes < 1) return 'Updated just now';
  if (minutes < 60) return `Updated ${minutes} min ago`;
  return `Updated ${Math.floor(minutes / 60)} h ago`;
};

/** The person's own setup step: connecting their assistant. Its help is in the panel. */
const CONNECT = 'onboarding:assistant';

/** To do rows show a drag handle in the marker column on hover (designs/16-work.md). */
const Handle: FC<{ children: ReactNode }> = ({ children }) => (
  <span className="flex size-4 items-center justify-center">
    <span className="flex group-hover:hidden">{children}</span>
    <GripVertical
      className="hidden size-4 cursor-grab text-ink-muted group-hover:block"
      aria-label="Drag to reorder"
    />
  </span>
);

const Marker: FC<{ task: WorkTaskPublic; movable?: boolean }> = ({ task, movable }) => {
  if (task.state === 'in_progress' && quietSince(task)) {
    return (
      <span className="flex size-4 items-center justify-center" aria-label="No activity">
        <span className="size-3 rounded-full border-2 border-ink-muted opacity-60" />
      </span>
    );
  }
  if (task.state === 'in_progress') {
    return (
      <LoaderCircle
        className="size-4 text-ink-muted motion-safe:animate-spin"
        aria-label="In progress"
      />
    );
  }
  if (task.state === 'waiting') {
    return <Pause className="size-4 fill-current text-warning" aria-label="Waiting for you" />;
  }
  const idle = isBlocked(task) ? (
    <Lock
      className={cn('size-4', warmLock(task) ? 'text-warning' : 'text-ink-muted')}
      aria-label="Blocked"
    />
  ) : (
    <span className="size-4" aria-hidden />
  );
  return movable ? <Handle>{idle}</Handle> : idle;
};

const TypeIcon: FC<{ kind: TaskKind; dim?: boolean }> = ({ kind, dim }) => {
  const Icon = KIND[kind].icon;
  return (
    <span
      className={cn(
        'flex size-7 flex-none items-center justify-center rounded-md',
        kind === 'incident' ? 'bg-critical-bg text-critical' : 'bg-unchecked-bg text-ink-secondary',
        dim && 'opacity-55'
      )}
      aria-hidden
    >
      <Icon className="size-4" />
    </span>
  );
};

/** The second line, with severity as a quiet coloured word. */
const Line: FC<{ task: WorkTaskPublic }> = ({ task }) => {
  const parts = task.line.split(' · ');
  return (
    <span className="truncate text-label text-ink-muted">
      {parts.map((part, i) => (
        <span key={`${part}-${i}`}>
          {i > 0 && ' · '}
          <span
            className={cn(
              part === 'Critical' && 'text-critical',
              part === 'Warning' && 'text-warning'
            )}
          >
            {part}
          </span>
        </span>
      ))}
      {task.state !== 'to_do' && (task.blocks?.length ?? 0) > 0 && (
        <> · Blocks: {named(task.blocks ?? [])}</>
      )}
    </span>
  );
};

const Chip: FC<{ children: ReactNode; warm?: boolean; initial?: string }> = ({
  children,
  warm,
  initial,
}) => (
  <span
    className={cn(
      'inline-flex h-7 max-w-[260px] items-center gap-2 rounded-full border px-2.5 text-label',
      warm ? 'border-transparent bg-warning-bg text-warning' : 'border-hairline text-ink-secondary'
    )}
  >
    {initial && (
      <span className="flex size-5 flex-none items-center justify-center rounded-full bg-wash text-[11px] text-ink">
        {initial}
      </span>
    )}
    <span className="truncate">{children}</span>
  </span>
);

interface Drag {
  onStart: () => void;
  /** Over this row: the drop goes before it (upper half) or after it (lower half). */
  onOver: (after: boolean) => void;
  onDrop: () => void;
  onEnd: () => void;
  /** A drop line above (before) or below (after) this row. */
  line?: 'before' | 'after';
  dragging: boolean;
}

interface RowProps {
  task: WorkTaskPublic;
  lit: boolean;
  dimmed: boolean;
  selected: boolean;
  onOpen: () => void;
  onHover: (key: string | null) => void;
  /** To do rows only: reordering by drag. */
  drag?: Drag;
}

const Row: FC<RowProps> = ({ task, lit, dimmed, selected, onOpen, onHover, drag }) => {
  const waiting = task.state === 'waiting';
  const blocked = isBlocked(task);
  const act = waiting ? action(task) : undefined;
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen();
        }
      }}
      onMouseEnter={() => onHover(task.key)}
      onMouseLeave={() => onHover(null)}
      draggable={drag ? true : undefined}
      onDragStart={
        drag
          ? (e) => {
              e.dataTransfer.effectAllowed = 'move';
              drag.onStart();
            }
          : undefined
      }
      onDragOver={
        drag
          ? (e) => {
              e.preventDefault();
              const box = e.currentTarget.getBoundingClientRect();
              drag.onOver(e.clientY > box.top + box.height / 2);
            }
          : undefined
      }
      onDrop={
        drag
          ? (e) => {
              e.preventDefault();
              drag.onDrop();
            }
          : undefined
      }
      onDragEnd={drag ? drag.onEnd : undefined}
      className={cn(
        'group relative grid cursor-pointer grid-cols-[16px_28px_minmax(0,1fr)_auto] items-center gap-3 border-t border-hairline px-5 py-3 first:border-t-0 hover:bg-wash',
        waiting && 'bg-warning-bg/40',
        selected && 'bg-wash',
        dimmed && 'opacity-60',
        drag?.dragging && 'opacity-50'
      )}
    >
      {drag?.line && (
        <span
          className={cn(
            'absolute right-5 left-5 h-0.5 rounded-full bg-warning',
            drag.line === 'before' ? '-top-px' : '-bottom-px'
          )}
          aria-hidden
        />
      )}
      {(waiting || lit) && (
        <span
          className="absolute top-3 bottom-3 left-0 w-[3px] rounded-r-sm bg-warning"
          aria-hidden
        />
      )}
      <Marker task={task} movable={Boolean(drag)} />
      <TypeIcon kind={task.kind} dim={blocked} />
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className={cn('truncate text-body', blocked ? 'text-ink-secondary' : 'text-ink')}>
          {task.title}
        </span>
        <Line task={task} />
        {quietSince(task) && (
          <span className="truncate text-label text-ink-muted">
            No activity since {timeLabel(quietSince(task)!)}
          </span>
        )}
        {blocked && (
          <span className="truncate text-label text-ink-muted">
            Blocked by: {named(task.blocked_by ?? [])}
          </span>
        )}
      </span>
      <span className="flex flex-col items-end gap-1">
        {task.holder && (
          <Chip initial={task.holder.person.charAt(0).toUpperCase()}>
            {holderName(task.holder)}
          </Chip>
        )}
        {waiting && <Chip warm>Waiting for you</Chip>}
        {act && (
          <Link
            href={act.href}
            scroll={false}
            onClick={(e) => e.stopPropagation()}
            className="text-label text-ink-secondary no-underline hover:text-ink hover:underline"
          >
            {act.label}
          </Link>
        )}
        {task.key === CONNECT && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpen();
            }}
            className="border-0 bg-transparent p-0 text-label text-ink-secondary hover:text-ink"
          >
            Show how →
          </button>
        )}
      </span>
    </div>
  );
};

/** "Show how": connecting an assistant (designs/16-work.md, frame 1). */
const ConnectHelp: FC<{ mcpUrl?: string | null }> = ({ mcpUrl }) => (
  <div className="flex flex-col gap-3">
    <ol className="m-0 flex list-decimal flex-col gap-1 pl-5 text-body text-ink">
      <li>Copy the Connexity MCP address.</li>
      <li>Add it to Claude Code or another assistant.</li>
      <li>Sign in when your assistant asks.</li>
    </ol>
    {mcpUrl ? (
      <ConnectAssistant mcpUrl={mcpUrl} />
    ) : (
      <span className="text-label text-ink-secondary">
        The MCP address is not configured on this deployment, so there is no way to connect an
        assistant yet.
      </span>
    )}
    <span className="text-label text-ink-muted">
      From here on, your assistant does the setup with you.
    </span>
  </div>
);

const Group: FC<{ label: string; children: ReactNode }> = ({ label, children }) => (
  <div className="flex flex-col gap-2">
    <span className="px-1 text-label text-ink-muted">{label}</span>
    <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
      {children}
    </section>
  </div>
);

const Fact: FC<{ label: string; children: ReactNode }> = ({ label, children }) => (
  <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-3 text-body">
    <span className="text-ink-muted">{label}</span>
    <span className="min-w-0 text-ink">{children}</span>
  </div>
);

const RefList: FC<{
  title: string;
  refs: WorkTaskRefPublic[];
  onOpen: (key: string) => void;
}> = ({ title, refs, onOpen }) =>
  refs.length ? (
    <div className="flex flex-col gap-2">
      <span className="text-label text-ink-muted">{title}</span>
      {refs.map((ref) => (
        <button
          key={ref.key}
          type="button"
          onClick={() => onOpen(ref.key)}
          className="flex items-center justify-between gap-3 rounded-lg border border-hairline bg-transparent px-3 py-2 text-left text-body text-ink hover:bg-wash"
        >
          <span className="truncate">{ref.title}</span>
          <span
            className={cn(
              'flex-none text-label',
              ref.waiting_for_person ? 'text-warning' : 'text-ink-muted'
            )}
          >
            {STATE_NAME[ref.state]}
          </span>
        </button>
      ))}
    </div>
  ) : null;

const Panel: FC<{
  task: WorkTaskPublic;
  mcpUrl?: string | null;
  onClose: () => void;
  onOpen: (key: string) => void;
}> = ({ task, mcpUrl, onClose, onOpen }) => {
  const act = task.state === 'waiting' ? action(task) : undefined;
  return (
    <aside
      aria-label="Task"
      className="fixed top-0 right-0 z-20 flex h-screen w-[400px] max-w-full flex-col gap-5 overflow-y-auto border-l border-hairline bg-surface-1 px-6 py-5"
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className={cn('text-label', task.state === 'waiting' ? 'text-warning' : 'text-ink-muted')}
        >
          {isBlocked(task)
            ? 'Blocked'
            : task.key === CONNECT
              ? 'To do · yours'
              : STATE_NAME[task.state]}
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="flex size-8 items-center justify-center rounded-md border-0 bg-transparent text-ink-secondary hover:bg-wash"
        >
          <X className="size-4" />
        </button>
      </div>
      <div className="flex items-start gap-3">
        <TypeIcon kind={task.kind} />
        <h2 className="m-0 text-pretty text-title font-medium text-ink">{task.title}</h2>
      </div>
      <div className="flex flex-col gap-2">
        <Fact label="Type">{KIND[task.kind].word}</Fact>
        {task.agent_name && <Fact label="Agent">{task.agent_name}</Fact>}
        <Fact label="Place">#{task.position} in the list</Fact>
        {task.holder && (
          <>
            <Fact label="Assistant">
              {task.holder.person}&apos;s {task.holder.assistant}
            </Fact>
            {task.holder.session && <Fact label="Session">{task.holder.session}</Fact>}
            <Fact label="Working since">{timeLabel(task.holder.taken_at)}</Fact>
            {quietSince(task) && (
              <Fact label="No activity since">
                <span className="flex flex-col gap-1">
                  <span>{timeLabel(quietSince(task)!)}</span>
                  <span className="text-label text-ink-muted">
                    Your assistant hasn&apos;t asked Connexity for its next task since then.
                    The task stays with this session until the assistant moves on.
                  </span>
                </span>
              </Fact>
            )}
          </>
        )}
      </div>
      {task.key === CONNECT && <ConnectHelp mcpUrl={mcpUrl} />}
      <RefList title="Blocks" refs={task.blocks ?? []} onOpen={onOpen} />
      <RefList title="Blocked by" refs={task.blocked_by ?? []} onOpen={onOpen} />
      <div className="flex flex-col gap-2 border-t border-hairline pt-4">
        {act && (
          <Link
            href={act.href}
            scroll={false}
            onClick={onClose}
            className="text-body text-ink no-underline hover:underline"
          >
            {act.label}
          </Link>
        )}
        {task.issue_id && (
          <Link
            href={UrlGenerator.issue(task.issue_id)}
            className="text-body text-ink-secondary no-underline hover:text-ink"
          >
            Open the issue
          </Link>
        )}
        {task.agent_id && (
          <Link
            href={UrlGenerator.agent(task.agent_id)}
            className="text-body text-ink-secondary no-underline hover:text-ink"
          >
            Open the agent
          </Link>
        )}
      </div>
    </aside>
  );
};

const plural = (n: number, word: string) => `${n} ${n === 1 ? word : `${word}s`}`;

/** Work (designs/screens/Connexity Work.dc.html), read only. */
export const WorkView: FC<{ work: WorkPublic }> = ({ work }) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [doneOpen, setDoneOpen] = useState(false);
  const [teamOpen, setTeamOpen] = useState(false);
  const router = useRouter();
  // The agent whose question cards are open under its row (?answer=<agent id>).
  const answering = useSearchParams().get('answer');
  const closeCards = () => router.replace(UrlGenerator.work(), { scroll: false });
  const [moving, startMove] = useTransition();
  // A move shows at once; it applies only to the page it was made on, so a refresh
  // brings the server's order back.
  const [optimistic, setOptimistic] = useState<{ basedOn: WorkPublic; keys: string[] } | null>(
    null
  );
  const [dragKey, setDragKey] = useState<string | null>(null);
  const [drop, setDrop] = useState<{ key: string; after: boolean } | null>(null);
  const [moveError, setMoveError] = useState<string | null>(null);
  // When this list came from the server, and the clock that ages it.
  const [loadedAt, setLoadedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  const [refreshing, startRefresh] = useTransition();
  useEffect(() => {
    setLoadedAt(Date.now());
    setNow(Date.now());
  }, [work]);
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(tick);
  }, []);
  const refresh = () => startRefresh(() => router.refresh());

  const all = [...work.in_progress, ...work.to_do];
  const byKey = new Map(all.map((task) => [task.key, task]));
  const toDo =
    optimistic && optimistic.basedOn === work
      ? optimistic.keys.flatMap((key) => byKey.get(key) ?? [])
      : work.to_do;

  const endDrag = () => {
    setDragKey(null);
    setDrop(null);
  };

  const move = () => {
    const key = dragKey;
    const target = drop;
    endDrag();
    if (!key || !target || target.key === key) return;
    const keys = toDo.map((task) => task.key).filter((k) => k !== key);
    const at = keys.indexOf(target.key) + (target.after ? 1 : 0);
    keys.splice(at, 0, key);
    const before = keys[at + 1] ?? null;
    setMoveError(null);
    setOptimistic({ basedOn: work, keys });
    startMove(async () => {
      const result = await moveWorkTaskAction(key, before);
      if (isErrorApiResult(result)) {
        setOptimistic(null);
        const detail = (result.error as { detail?: unknown } | undefined)?.detail;
        setMoveError(typeof detail === 'string' ? detail : 'That move did not go through.');
      }
      router.refresh();
    });
  };
  const hover = hovered ? byKey.get(hovered) : undefined;
  const related = new Set(
    hover ? [...(hover.blocks ?? []), ...(hover.blocked_by ?? [])].map((ref) => ref.key) : []
  );
  const open = selected ? byKey.get(selected) : undefined;

  const row = (task: WorkTaskPublic) => (
    <Fragment key={task.key}>
      <Row
        task={task}
        lit={related.has(task.key)}
        dimmed={related.size > 0 && !related.has(task.key) && task.key !== hovered}
        selected={task.key === selected}
        onOpen={() => setSelected(task.key)}
        onHover={setHovered}
        drag={
          task.state === 'to_do' && task.kind !== 'incident' && task.key !== CONNECT
            ? {
                onStart: () => setDragKey(task.key),
                onOver: (after) => setDrop({ key: task.key, after }),
                onDrop: move,
                onEnd: endDrag,
                line:
                  dragKey && drop?.key === task.key && dragKey !== task.key
                    ? drop.after
                      ? 'after'
                      : 'before'
                    : undefined,
                dragging: dragKey === task.key,
              }
            : undefined
        }
      />
      {task.kind === 'clarifications' &&
        task.state === 'waiting' &&
        task.agent_id &&
        task.agent_id === answering && (
          <QuestionCards agentId={task.agent_id} onClose={closeCards} />
        )}
    </Fragment>
  );

  const sessions = work.sessions;
  // A session is quiet when every task it holds is.
  const bySession = new Map<string, boolean>();
  for (const task of work.in_progress) {
    if (!task.holder) continue;
    const id = holderName(task.holder);
    bySession.set(id, (bySession.get(id) ?? true) && Boolean(quietSince(task)));
  }
  const quiet = [...bySession.values()].filter(Boolean).length;
  const working = sessions.length - quiet;
  const caption = (
    <span
      className="relative inline-block"
      onMouseEnter={() => setTeamOpen(true)}
      onMouseLeave={() => setTeamOpen(false)}
    >
      <span className="cursor-default border-b border-dotted border-ink-muted">
        {!work.assistant_connected
          ? 'No assistant connected'
          : sessions.length
            ? [working > 0 && `${plural(working, 'session')} working`, quiet > 0 && `${quiet} quiet`]
                .filter(Boolean)
                .join(', ')
            : 'No assistant working'}
      </span>
      {teamOpen && sessions.length > 0 && (
        <span className="absolute top-6 left-0 z-10 flex w-[320px] flex-col gap-2 rounded-lg border border-hairline bg-surface-2 p-3 shadow-lg">
          {sessions.map((s) => (
            <span key={`${s.person}-${s.assistant}-${s.session}`} className="flex flex-col">
              <span className="text-body text-ink">{holderName({ ...s, taken_at: '' })}</span>
              <span className="truncate text-label text-ink-muted">{s.task}</span>
            </span>
          ))}
        </span>
      )}
    </span>
  );

  return (
    <div className="flex max-w-[960px] flex-col gap-5">
      <PageBar
        title="Work"
        caption={caption}
        actions={
          <span className="flex items-center gap-2 text-label text-ink-muted">
            {updatedLabel(loadedAt, now)}
            <button
              type="button"
              onClick={refresh}
              disabled={refreshing}
              aria-label="Refresh"
              className="flex size-8 items-center justify-center rounded-md border-0 bg-transparent text-ink-secondary hover:bg-wash hover:text-ink"
            >
              <RotateCw
                className={cn('size-4', refreshing && 'motion-safe:animate-spin')}
                aria-hidden
              />
            </button>
          </span>
        }
      />

      <div className="flex flex-col gap-1">
        <h2 className="m-0 text-body font-medium text-ink">Assistant tasks</h2>
        <span className="text-label text-ink-muted">
          Your assistant works down this list from the top. You can reorder what hasn&apos;t
          started.
        </span>
      </div>

      {all.length === 0 ? (
        <section className="rounded-xl border border-hairline bg-surface-1 px-6 py-8 text-center text-ink-secondary">
          Nothing waits. Your assistant is up to date.
        </section>
      ) : (
        <>
          {work.in_progress.length > 0 && (
            <Group label="In progress">{work.in_progress.map(row)}</Group>
          )}
          {toDo.length > 0 && (
            <div className={cn('flex flex-col gap-2', moving && 'opacity-80')}>
              <Group label="To do">{toDo.map(row)}</Group>
              {moveError && <span className="px-1 text-label text-critical">{moveError}</span>}
            </div>
          )}
        </>
      )}

      {work.done.length > 0 && (
        <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
          <button
            type="button"
            aria-expanded={doneOpen}
            onClick={() => setDoneOpen(!doneOpen)}
            className="flex min-h-12 w-full items-center gap-3 border-0 bg-transparent px-5 text-left text-body text-ink-secondary hover:bg-wash"
          >
            <CircleCheck className="size-4 text-passed" aria-hidden />
            <span className="flex-1">{work.done.length} done this week</span>
            {doneOpen ? (
              <ChevronDown className="size-4" aria-hidden />
            ) : (
              <ChevronRight className="size-4" aria-hidden />
            )}
          </button>
          {doneOpen &&
            work.done.map((d) => {
              const cells = (
                <>
                  <span aria-hidden />
                  <span className="truncate text-body text-ink">{d.title}</span>
                  <span className="truncate text-label text-ink-secondary">{d.by}</span>
                  <span className="text-right text-label whitespace-nowrap text-ink-muted">
                    {timeLabel(d.at)}
                  </span>
                </>
              );
              const className =
                'grid min-h-11 grid-cols-[16px_minmax(0,1fr)_minmax(0,200px)_96px] items-center gap-3 border-t border-hairline px-5 py-2';
              return d.link ? (
                <Link
                  key={`${d.title}-${d.at}`}
                  href={doneHref(d.link)}
                  className={cn(className, 'no-underline hover:bg-wash')}
                >
                  {cells}
                </Link>
              ) : (
                <div key={`${d.title}-${d.at}`} className={className}>
                  {cells}
                </div>
              );
            })}
        </section>
      )}

      {open && (
        <Panel
          task={open}
          mcpUrl={work.mcp_url}
          onClose={() => setSelected(null)}
          onOpen={(key) => setSelected(key)}
        />
      )}
    </div>
  );
};

export default WorkView;
