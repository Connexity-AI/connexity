'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { ChevronDown, ChevronRight } from 'lucide-react';

import { NumberTile } from '@workspace/ui/components/number-tile';
import { PageBar } from '@workspace/ui/components/page-bar';
import { cn } from '@workspace/ui/lib/utils';

import { decideClarificationAction } from '@/actions/clarifications';
import { parseTime } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';
import { isErrorApiResult } from '@/utils/api';

import type { ClarificationListPage, ClarificationPublic } from '@/client/types.gen';
import type { Option } from '@/components/common/picker';
import type { FC, ReactNode } from 'react';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const PAGE = 5;

/** "6 Nov" in the viewer's time zone. */
const dayLabel = (iso: string) => {
  const date = parseTime(iso);
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
};

const evidence = (item: ClarificationPublic) => {
  const spec = item.spec_version ? ` · spec version ${item.spec_version}` : '';
  if (!item.calls_seen) return `Raised from a prompt change${spec}`;
  return `Seen on ${item.calls_seen} ${item.calls_seen === 1 ? 'call' : 'calls'}${spec}`;
};

const answerOf = (item: ClarificationPublic) => item.answers.find((a) => a.letter === item.answer);

const MoreLine: FC<{ count: number; onMore: () => void; label?: string }> = ({
  count,
  onMore,
  label = 'more',
}) =>
  count > 0 ? (
    <button
      type="button"
      onClick={onMore}
      className="w-full border-0 border-t border-hairline bg-transparent px-6 py-3 text-left text-body text-ink-secondary hover:bg-wash"
    >
      {count.toLocaleString()} {label}
    </button>
  ) : null;

const Card: FC<{ item: ClarificationPublic }> = ({ item }) => {
  const router = useRouter();
  const [picked, setPicked] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [pending, startTransition] = useTransition();
  const conflict = Boolean(item.replaces);
  const choice = item.answers.find((a) => a.letter === picked);

  const decide = (answer: string) => {
    setFailed(false);
    startTransition(async () => {
      const result = await decideClarificationAction(item.id, answer);
      if (isErrorApiResult(result)) {
        setFailed(true);
        return;
      }
      setPicked(null);
      router.refresh();
    });
  };

  return (
    <div
      className={cn(
        'flex flex-col gap-3 border-t border-hairline px-6 py-5 first:border-t-0',
        pending && 'opacity-70'
      )}
    >
      <div className="flex flex-wrap items-center gap-2 text-label text-ink-secondary">
        <Link href={UrlGenerator.agent(item.agent_id)} className="text-ink-secondary">
          {item.agent_name}
        </Link>
        <span aria-hidden>·</span>
        <span>{conflict ? 'Conflict with an earlier answer' : 'Clarification'}</span>
      </div>
      <p className="m-0 text-pretty text-body text-ink">{item.question}</p>
      <span className="text-label text-ink-muted">
        {evidence(item)}
        {item.call_ids && item.call_ids[0] && (
          <>
            {' · '}
            <Link href={UrlGenerator.call(item.call_ids[0])} className="text-ink-secondary">
              Open a call
            </Link>
          </>
        )}
      </span>
      {conflict && item.replaces?.text && (
        <div className="flex flex-col gap-1 rounded-lg border border-hairline px-4 py-3">
          <span className="text-label text-ink-muted">Earlier answer</span>
          <span className="text-body text-ink">“{item.replaces.text}”</span>
        </div>
      )}
      {choice ? (
        <div className="flex flex-col gap-3 rounded-lg border border-border-control bg-wash px-4 py-3">
          <p className="m-0 text-body text-ink">
            Answer {choice.letter}: “{choice.rule}”
          </p>
          <p className="m-0 text-label text-ink-secondary">
            This becomes a rule in the spec. An answer is final.
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={pending}
              onClick={() => decide(choice.letter)}
              className="h-9 rounded-lg border-0 bg-ink px-4 text-body text-surface-1"
            >
              Confirm
            </button>
            <button
              type="button"
              disabled={pending}
              onClick={() => setPicked(null)}
              className="h-9 rounded-lg border border-border-control bg-transparent px-4 text-body text-ink hover:bg-surface-1"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {item.answers.map((answer) => (
            <button
              key={answer.letter}
              type="button"
              title={answer.rule}
              disabled={pending}
              onClick={() => setPicked(answer.letter)}
              className="flex h-9 items-center gap-2 rounded-lg border border-border-control bg-transparent px-3 text-body text-ink hover:bg-wash"
            >
              <span className="text-label text-ink-muted">{answer.letter}</span>
              {answer.label}
            </button>
          ))}
          <button
            type="button"
            disabled={pending}
            onClick={() => decide('park')}
            className="h-9 border-0 bg-transparent px-2 text-body text-ink-secondary hover:text-ink"
          >
            Park
          </button>
        </div>
      )}
      {failed && (
        <span className="text-label text-critical">
          That did not go through. Refresh the page and try again.
        </span>
      )}
    </div>
  );
};

const Section: FC<{ title: string; count: number; children: ReactNode }> = ({
  title,
  count,
  children,
}) => {
  const [open, setOpen] = useState(false);
  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex min-h-12 w-full items-center gap-2 border-0 bg-transparent px-6 text-left text-body text-ink hover:bg-wash"
      >
        <Chevron className="size-4 text-ink-secondary" aria-hidden />
        <span className="font-medium">{title}</span>
        <span className="text-label text-ink-secondary">{count.toLocaleString()}</span>
      </button>
      {open && children}
    </section>
  );
};

const ROW = 'grid grid-cols-[200px_minmax(0,1fr)_minmax(0,240px)_160px] items-center gap-4 px-6';

interface Props {
  open: ClarificationListPage;
  /** Answered ones of the last 7 days, newest first; counts for the whole workspace. */
  answered: ClarificationListPage;
  parked: ClarificationListPage;
  agents: Option[];
  agentId?: string;
  shown: { open: number; answered: number; parked: number };
}

/** Action items (designs/screens/Connexity Action items.dc.html): clarifications only. */
export const ActionItemsView: FC<Props> = ({ open, answered, parked, agents, agentId, shown }) => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();

  const go = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    const search = next.toString();
    startTransition(() =>
      router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false })
    );
  };
  const [reopenFailed, setReopenFailed] = useState(false);
  const reopen = (id: string) =>
    startTransition(async () => {
      const result = await decideClarificationAction(id, 'reopen');
      setReopenFailed(isErrorApiResult(result));
      router.refresh();
    });

  const counts = open.counts;
  const thisWeek = answered.data;

  return (
    <div className={cn('flex max-w-[1120px] flex-col gap-6', pending && 'opacity-70')}>
      <PageBar
        title="Action items"
        caption={
          agentId
            ? `${counts.open} open for this agent`
            : 'Across all agents · most important first'
        }
        actions={
          <Picker
            label="Agent"
            value={agentId}
            options={agents}
            onPick={(value) => go({ agent: value, shown: undefined })}
            align="end"
          />
        }
      />

      <div className="grid grid-cols-3 gap-3">
        <NumberTile label="Open" value={counts.open.toLocaleString()} />
        <NumberTile
          label="Answered this week"
          value={(counts.answered_this_week ?? 0).toLocaleString()}
        />
        <NumberTile label="Parked" value={counts.parked.toLocaleString()} />
      </div>

      <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
        {open.data.length === 0 ? (
          <div className="px-6 py-8 text-center text-ink-secondary">Nothing needs your input</div>
        ) : (
          open.data.map((item) => <Card key={item.id} item={item} />)
        )}
        <MoreLine
          count={counts.open - open.data.length}
          onMore={() => go({ shown: String(shown.open + PAGE) })}
        />
      </section>

      {(counts.answered_this_week ?? 0) > 0 && (
        <Section title="Answered" count={counts.answered_this_week ?? 0}>
          <div
            className={cn(ROW, 'min-h-10 border-t border-hairline text-label text-ink-secondary')}
          >
            <span>Agent</span>
            <span>Question</span>
            <span>Answer</span>
            <span>Answered by</span>
          </div>
          {thisWeek.map((a) => (
            <div key={a.id} className={cn(ROW, 'min-h-11 border-t border-hairline py-2 text-body')}>
              <span className="truncate text-ink-secondary">{a.agent_name}</span>
              <span className="text-pretty text-ink">{a.question}</span>
              <span className="text-ink">{answerOf(a)?.label ?? a.answer}</span>
              <span className="text-label text-ink-muted">
                {a.decided_by ? `${a.decided_by}, ` : ''}
                {a.decided_at ? dayLabel(a.decided_at) : ''}
              </span>
            </div>
          ))}
          <MoreLine
            count={(counts.answered_this_week ?? 0) - thisWeek.length}
            label="more this week"
            onMore={() => go({ answered: String(shown.answered + PAGE) })}
          />
        </Section>
      )}

      {counts.parked > 0 && (
        <Section title="Parked" count={counts.parked}>
          <div
            className={cn(ROW, 'min-h-10 border-t border-hairline text-label text-ink-secondary')}
          >
            <span>Agent</span>
            <span>Question</span>
            <span>Parked</span>
            <span />
          </div>
          {parked.data.map((p) => (
            <div key={p.id} className={cn(ROW, 'min-h-11 border-t border-hairline py-2 text-body')}>
              <span className="truncate text-ink-secondary">{p.agent_name}</span>
              <span className="text-pretty text-ink">{p.question}</span>
              <span className="text-label text-ink-muted">
                {p.decided_at ? dayLabel(p.decided_at) : ''}
              </span>
              <span className="flex justify-end">
                <button
                  type="button"
                  onClick={() => reopen(p.id)}
                  className="h-8 rounded-lg border border-border-control bg-transparent px-3 text-body text-ink hover:bg-wash"
                >
                  Reopen
                </button>
              </span>
            </div>
          ))}
          {reopenFailed && (
            <p className="m-0 border-t border-hairline px-6 py-3 text-label text-critical">
              That question could not be reopened; it may have been answered meanwhile.
            </p>
          )}
          <MoreLine
            count={counts.parked - parked.data.length}
            onMore={() => go({ parked: String(shown.parked + PAGE) })}
          />
        </Section>
      )}
    </div>
  );
};
