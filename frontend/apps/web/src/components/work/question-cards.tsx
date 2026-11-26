'use client';

import { useEffect, useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { useQueryClient } from '@tanstack/react-query';

import { cn } from '@workspace/ui/lib/utils';

import { answerQuestionsAction, openQuestionsAction } from '@/actions/clarifications';
import { WORK_KEY } from '@/components/work/work-query';
import { isErrorApiResult } from '@/utils/api';

import type { CardAnswer } from '@/actions/clarifications';
import type { ClarificationPublic } from '@/client/types.gen';
import type { FC } from 'react';

const OTHER = 'other';

/** "Seen on 9 calls", or where a question without calls came from. */
const why = (q: ClarificationPublic) =>
  q.calls_seen
    ? `Seen on ${q.calls_seen} ${q.calls_seen === 1 ? 'call' : 'calls'}`
    : 'Raised from the prompt';

interface Props {
  agentId: string;
  onClose: () => void;
}

/**
 * The person answers an agent's open questions one card at a time, under its waiting
 * row on Work (designs/16-work.md, frames 4 and 5; plans/2026-11-16-question-cards.md).
 * Choices are sent together after the last card, so Back can still change one.
 */
export const QuestionCards: FC<Props> = ({ agentId, onClose }) => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [questions, setQuestions] = useState<ClarificationPublic[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [at, setAt] = useState(0);
  const [picks, setPicks] = useState<Record<string, CardAnswer>>({});
  const [otherOpen, setOtherOpen] = useState(false);
  const [otherText, setOtherText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sending, startSending] = useTransition();

  useEffect(() => {
    let live = true;
    openQuestionsAction(agentId).then((result) => {
      if (!live) return;
      if (isErrorApiResult(result) || !result.data) setLoadFailed(true);
      else setQuestions(result.data.data);
    });
    return () => {
      live = false;
    };
  }, [agentId]);

  const finish = (all: Record<string, CardAnswer>) => {
    const answers = Object.values(all);
    if (answers.length === 0) {
      onClose();
      return;
    }
    setError(null);
    startSending(async () => {
      const result = await answerQuestionsAction(answers);
      if (isErrorApiResult(result)) {
        setError('Those answers did not go through. Refresh the page and try again.');
        return;
      }
      onClose();
      // The answered questions leave Work's list now, not at its next reload.
      void queryClient.invalidateQueries({ queryKey: WORK_KEY });
      router.refresh();
    });
  };

  const next = (all: Record<string, CardAnswer>) => {
    setOtherOpen(false);
    setOtherText('');
    if (questions && at + 1 < questions.length) setAt(at + 1);
    else finish(all);
  };

  if (loadFailed) {
    return (
      <p className="m-0 border-t border-hairline px-5 py-4 text-label text-critical">
        The questions could not be loaded. Refresh the page and try again.
      </p>
    );
  }
  if (!questions) {
    return (
      <p className="m-0 border-t border-hairline px-5 py-4 text-label text-ink-muted">
        Loading the questions…
      </p>
    );
  }
  if (questions.length === 0) {
    return (
      <p className="m-0 border-t border-hairline px-5 py-4 text-label text-ink-muted">
        No questions are open for this agent any more.
      </p>
    );
  }

  const q = questions[at]!;
  const picked = picks[q.id];
  const choose = (answer: string, text?: string) => {
    const all = { ...picks, [q.id]: { clarificationId: q.id, answer, text } };
    setPicks(all);
    next(all);
  };

  return (
    <div
      className={cn(
        'flex flex-col gap-4 border-t border-hairline bg-surface-0 px-5 py-5 sm:pl-[72px]',
        sending && 'opacity-70'
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex flex-col gap-2">
        {/* What the question is about (designs/24-clarification-on-rule.md). */}
        {q.kind === 'clarification' && q.rule?.text && (
          <div className="flex flex-col gap-0.5">
            <span className="text-label text-ink-muted">About the rule</span>
            <span className="text-pretty text-label text-ink-secondary">“{q.rule.text}”</span>
          </div>
        )}
        {q.kind === 'prompt_gap' && (
          <span className="text-label text-ink-muted">The prompt doesn’t cover this</span>
        )}
        <div className="flex flex-col gap-1">
          <p className="m-0 text-pretty text-body text-ink">{q.question}</p>
          <span className="text-label text-ink-muted">{why(q)}</span>
          {q.replaces_sentence && (
            <span className="text-label text-ink-muted">
              Earlier answer: “{q.replaces_sentence}”
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {q.answers.map((a) => (
          <button
            key={a.letter}
            type="button"
            disabled={sending}
            onClick={() => choose(a.letter)}
            className={cn(
              'flex min-h-11 flex-col items-start justify-center gap-0.5 rounded-lg border px-4 py-2.5 text-left text-body text-ink hover:bg-wash',
              picked?.answer === a.letter
                ? 'border-ink bg-wash'
                : 'border-border-control bg-surface-1'
            )}
          >
            <span>{a.label}</span>
            <span className="text-pretty text-label text-ink-secondary">
              {q.kind === 'prompt_gap' ? 'Prompt would say: ' : 'Adds: '}
              {a.sentence}
            </span>
          </button>
        ))}
        <button
          type="button"
          disabled={sending}
          onClick={() => setOtherOpen(!otherOpen)}
          className={cn(
            'min-h-11 rounded-lg border px-4 py-2.5 text-left text-body text-ink hover:bg-wash',
            otherOpen || picked?.answer === OTHER
              ? 'border-ink bg-wash'
              : 'border-border-control bg-surface-1'
          )}
        >
          Something else
        </button>
        {otherOpen && (
          <div className="flex flex-col gap-2">
            <textarea
              value={otherText}
              onChange={(e) => setOtherText(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder={
                q.kind === 'prompt_gap'
                  ? 'Tell the assistant what the agent should do'
                  : 'Write the clarification in your own words'
              }
              className="w-full resize-none rounded-lg border border-border-control bg-surface-1 px-3 py-2 text-body text-ink placeholder:text-ink-muted"
            />
            <button
              type="button"
              disabled={sending || !otherText.trim()}
              onClick={() => choose(OTHER, otherText.trim())}
              className="h-10 self-start rounded-lg border-0 bg-ink px-4 text-body text-surface-1 disabled:opacity-50"
            >
              Save answer
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1">
        <span className="flex-1 text-label text-ink-secondary">
          {at + 1} of {questions.length}
        </span>
        <button
          type="button"
          disabled={at === 0 || sending}
          onClick={() => {
            // Back to the previous card, with its choice still there to change.
            const before = picks[questions[at - 1]!.id];
            const other = before?.answer === OTHER;
            setOtherOpen(other);
            setOtherText(other ? (before?.text ?? '') : '');
            setAt(at - 1);
          }}
          className="h-8 rounded-md border-0 bg-transparent px-2.5 text-label text-ink-secondary hover:bg-wash hover:text-ink disabled:opacity-40"
        >
          Back
        </button>
        <button
          type="button"
          disabled={sending}
          onClick={() => {
            const { [q.id]: _, ...rest } = picks;
            setPicks(rest);
            next(rest);
          }}
          className="h-8 rounded-md border-0 bg-transparent px-2.5 text-label text-ink-secondary hover:bg-wash hover:text-ink"
        >
          Skip
        </button>
      </div>
      {error && <span className="text-label text-critical">{error}</span>}
    </div>
  );
};

export default QuestionCards;
