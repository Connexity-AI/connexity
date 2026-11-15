'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { Check, ChevronDown, ChevronRight } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { confirmSuggestionsAction } from '@/actions/clarifications';
import { isErrorApiResult } from '@/utils/api';

import type { ClarificationPublic } from '@/client/types.gen';
import type { FC } from 'react';

const FIRST = 10;

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

const suggested = (item: ClarificationPublic) =>
  item.answers.find((a) => a.letter === item.suggestion?.answer);

interface Props {
  /** Open questions with a confident suggestion. */
  items: ClarificationPublic[];
  collapsed: boolean;
  onCollapsed: (collapsed: boolean) => void;
  /** Ids the person unticked; they stay suggestions, decided on their cards. */
  off: Set<string>;
  onToggle: (id: string) => void;
  onConfirmed: (answers: number, agents: number) => void;
}

/** The batch of confident suggestions (designs/14-suggested-answers.md, section 1). */
export const SuggestionsPanel: FC<Props> = ({
  items,
  collapsed,
  onCollapsed,
  off,
  onToggle,
  onConfirmed,
}) => {
  const router = useRouter();
  const [all, setAll] = useState(false);
  const [failed, setFailed] = useState(false);
  const [pending, startTransition] = useTransition();
  const picked = items.filter((item) => !off.has(item.id));
  const rows = all ? items : items.slice(0, FIRST);
  const Chevron = collapsed ? ChevronRight : ChevronDown;

  const confirm = () => {
    if (!picked.length) return;
    setFailed(false);
    startTransition(async () => {
      const result = await confirmSuggestionsAction(
        picked.map((item) => ({ clarificationId: item.id, answer: item.suggestion?.answer ?? '' }))
      );
      if (isErrorApiResult(result)) {
        // All or nothing: one answered elsewhere meanwhile refuses the batch. Reload
        // the list so the person can confirm the rest.
        setFailed(true);
        router.refresh();
        return;
      }
      onConfirmed(picked.length, new Set(picked.map((item) => item.agent_id)).size);
      router.refresh();
    });
  };

  return (
    <section
      className={cn(
        'overflow-hidden rounded-xl border border-hairline bg-surface-1',
        pending && 'opacity-70'
      )}
    >
      <button
        type="button"
        aria-expanded={!collapsed}
        onClick={() => onCollapsed(!collapsed)}
        className="flex w-full items-start gap-3 border-0 bg-transparent px-6 py-[18px] text-left hover:bg-wash"
      >
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="text-pretty text-body font-medium text-ink">
            Your assistant suggests answers for {plural(items.length, 'question')} it is confident
            about.
          </span>
          <span className="text-label text-ink-muted">
            Check them, then confirm. Each becomes a rule in its agent&apos;s spec.
          </span>
        </span>
        <Chevron className="mt-[3px] size-4 flex-none text-ink-secondary" aria-hidden />
      </button>
      {!collapsed && (
        <>
          {rows.map((item) => {
            const on = !off.has(item.id);
            const answer = suggested(item);
            return (
              <button
                key={item.id}
                type="button"
                role="checkbox"
                aria-checked={on}
                onClick={() => onToggle(item.id)}
                className="grid w-full grid-cols-[16px_160px_minmax(0,1fr)_minmax(0,1.2fr)] items-start gap-4 border-0 border-t border-hairline bg-transparent px-6 py-3 text-left text-body text-ink hover:bg-wash"
              >
                <span
                  className={cn(
                    'mt-[3px] flex size-4 items-center justify-center rounded',
                    on ? 'bg-accent-ink text-on-accent' : 'border border-border-control'
                  )}
                >
                  {on && <Check className="size-3" aria-hidden />}
                </span>
                <span className="text-label text-ink-secondary">{item.agent_name}</span>
                <span title={item.question} className="min-w-0 truncate">
                  {item.question}
                </span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="font-medium">{answer?.label}</span>
                  <span className="text-pretty text-label text-ink-muted">
                    {answer?.rule} · {item.suggestion?.why}
                  </span>
                </span>
              </button>
            );
          })}
          {!all && items.length > FIRST && (
            <button
              type="button"
              onClick={() => setAll(true)}
              className="flex min-h-10 w-full items-center border-0 border-t border-hairline bg-transparent pr-6 pl-14 text-left text-label text-ink-secondary hover:bg-wash hover:text-ink"
            >
              and {items.length - FIRST} more
            </button>
          )}
          <div className="flex items-center gap-2 border-t border-hairline px-6 py-4">
            <button
              type="button"
              disabled={!picked.length || pending}
              onClick={confirm}
              className={cn(
                'h-9 rounded-lg border-0 bg-accent-ink px-3.5 text-body font-medium text-on-accent',
                !picked.length && 'opacity-40'
              )}
            >
              Confirm {plural(picked.length, 'answer')}
            </button>
            <button
              type="button"
              onClick={() => onCollapsed(true)}
              className="h-9 rounded-lg border-0 bg-transparent px-3 text-body text-ink-secondary hover:bg-wash hover:text-ink"
            >
              Review one by one
            </button>
            {failed && (
              <span className="text-label text-critical">
                Nothing was recorded: one of these may have been answered meanwhile. The list is up
                to date now; confirm again.
              </span>
            )}
          </div>
        </>
      )}
    </section>
  );
};
