'use client';

import { useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronRight } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { countAgainAction } from '@/actions/issues';
import { modelName } from '@/components/calls/call-view';
import { clock, timeLabel } from '@/components/calls/format';
import { IssuesService } from '@/client/sdk.gen';
import { isErrorApiResult } from '@/utils/api';

import type { IssuePagePublic, NotCountedPublic, NotCountedRow } from '@/client/types.gen';
import type { FC, RefObject } from 'react';

type Group = NotCountedPublic['group'];

// Rows shown before "Show all", and the page size when showing all.
const FIRST = 10;
const ALL_PAGE = 100;

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const monthDay = (iso: string) => {
  const d = new Date(iso);
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`;
};

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** "8 findings marked as false positives · 2 flags dismissed by the model". */
export const notCountedSummary = (issue: IssuePagePublic) =>
  [
    issue.false_positives
      ? plural(
          issue.false_positives,
          'finding marked as a false positive',
          'findings marked as false positives'
        )
      : null,
    issue.dismissed
      ? plural(issue.dismissed, 'flag dismissed by the model', 'flags dismissed by the model')
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

const load = async (
  issueId: string,
  group: Group,
  offset: number,
  limit: number
): Promise<NotCountedPublic> => {
  const result = await IssuesService.getNotCounted({
    path: { issue_id: issueId },
    query: { group, offset, limit },
  });
  if (!result.data) throw new Error('The list could not be loaded.');
  return result.data;
};

/** Every row past the first page, a page of 100 at a time. */
const loadRest = async (issueId: string, group: Group): Promise<NotCountedRow[]> => {
  const rows: NotCountedRow[] = [];
  let offset: number | null | undefined = FIRST;
  while (offset != null) {
    const page = await load(issueId, group, offset, ALL_PAGE);
    rows.push(...(page.rows ?? []));
    offset = page.next_offset;
  }
  return rows;
};

const Row: FC<{
  row: NotCountedRow;
  group: Group;
  confirming: boolean;
  busy: boolean;
  onAsk: () => void;
  onCancel: () => void;
  onConfirm: () => void;
}> = ({ row, group, confirming, busy, onAsk, onCancel, onConfirm }) => {
  const act = group === 'false_positives' ? 'Undo' : 'Bring back';
  const by =
    group === 'false_positives'
      ? `Marked by ${row.assistant ?? row.by ?? 'a person'}${row.at ? ` on ${monthDay(row.at)}` : ''}`
      : `Dismissed by ${modelName(row.model ?? 'the model')}${
          row.probability != null
            ? ` · flagged by the classifier, ${row.probability.toFixed(2)}`
            : ''
        }`;
  return (
    <div className="grid grid-cols-[160px_minmax(0,1fr)_auto] items-start gap-4 border-t border-hairline px-6 py-3">
      <div className="flex min-w-0 flex-col">
        <Link
          href={UrlGenerator.call(row.call_id, row.at_seconds ?? undefined)}
          title="Open the call"
          className="self-start whitespace-nowrap text-ink"
        >
          {timeLabel(row.started_at)}
        </Link>
        {row.at_seconds != null && (
          <span className="text-label text-ink-muted">at {clock(row.at_seconds)}</span>
        )}
      </div>
      <div className="flex min-w-0 flex-col">
        <span className="text-label text-ink-secondary">{by}</span>
        {row.reason && (
          <span title={row.reason} className="truncate">
            {row.reason}
          </span>
        )}
        {row.clarification && (
          <span title={row.clarification} className="truncate text-label text-ink-muted">
            Rests on: Clarified: {row.clarification}
          </span>
        )}
        {row.approved_by && (
          <span className="text-label text-ink-muted">Approved by {row.approved_by}</span>
        )}
      </div>
      <div className="relative">
        <button
          type="button"
          onClick={onAsk}
          className="h-8 whitespace-nowrap rounded-lg border border-border-control bg-transparent px-3 text-label text-ink hover:bg-wash"
        >
          {act}
        </button>
        {confirming && (
          <div className="absolute top-[38px] right-0 z-20 flex w-80 flex-col gap-3 rounded-xl border border-hairline bg-surface-2 p-4 shadow-lg">
            <span className="text-pretty">
              This finding will show on its call again and count in the score.
            </span>
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={onCancel}
                className="h-9 rounded-lg border-0 bg-transparent px-3 text-ink-secondary hover:bg-wash hover:text-ink"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={onConfirm}
                className="h-9 whitespace-nowrap rounded-lg border-0 bg-accent px-3.5 font-medium text-on-accent hover:opacity-90 disabled:opacity-60"
              >
                {act}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const GroupRows: FC<{
  issueId: string;
  group: Group;
  title: string;
  page: NotCountedPublic;
  confirm: string | null;
  setConfirm: (key: string | null) => void;
}> = ({ issueId, group, title, page, confirm, setConfirm }) => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [all, setAll] = useState(false);
  const [busy, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const rest = useQuery({
    queryKey: ['not-counted', issueId, group, 'rest'],
    queryFn: () => loadRest(issueId, group),
    enabled: all && page.next_offset != null,
  });

  if (page.total === 0) return null;
  const rows = [...(page.rows ?? []), ...(all && rest.data ? rest.data : [])];

  const countAgain = (row: NotCountedRow) => {
    setError(null);
    startTransition(async () => {
      const result = await countAgainAction(
        issueId,
        group === 'false_positives' && row.finding_id ? [row.finding_id] : [],
        group === 'dismissed' ? [row.call_id] : []
      );
      if (isErrorApiResult(result)) {
        setError('It could not be counted again. Try again.');
        return;
      }
      setConfirm(null);
      await queryClient.invalidateQueries({ queryKey: ['not-counted', issueId] });
      router.refresh();
    });
  };

  return (
    <>
      <div className="flex items-baseline gap-2 border-t border-hairline px-6 pt-4 pb-2">
        <h3 className="m-0 text-label font-medium">{title}</h3>
        <span className="text-label text-ink-muted">{page.total}</span>
      </div>
      {rows.map((row) => {
        const key = `${group}:${row.finding_id ?? row.call_id}`;
        return (
          <Row
            key={key}
            row={row}
            group={group}
            confirming={confirm === key}
            busy={busy}
            onAsk={() => setConfirm(confirm === key ? null : key)}
            onCancel={() => setConfirm(null)}
            onConfirm={() => countAgain(row)}
          />
        );
      })}
      {error && <div className="px-6 pb-3 text-label text-critical">{error}</div>}
      {!all && page.next_offset != null && (
        <button
          type="button"
          onClick={() => setAll(true)}
          className="flex w-full border-0 border-t border-hairline bg-transparent px-6 py-3.5 text-left text-label text-ink-secondary hover:text-ink"
        >
          Show all {page.total}
        </button>
      )}
      {all && rest.isPending && (
        <div className="border-t border-hairline px-6 py-3.5 text-label text-ink-muted">
          Loading…
        </div>
      )}
    </>
  );
};

/** What the issue does not count: findings marked as false positives, and flags the LLM
 * step dismissed. Closed by default; its rows load only when it is opened (Decided,
 * Dmytro 2026-11-27). */
export const NotCounted: FC<{
  issue: IssuePagePublic;
  open: boolean;
  setOpen: (open: boolean) => void;
  cardRef: RefObject<HTMLElement | null>;
}> = ({ issue, open, setOpen, cardRef }) => {
  const [confirm, setConfirm] = useState<string | null>(null);
  const marked = issue.false_positives ?? 0;
  const dismissed = issue.dismissed ?? 0;
  // Both groups' first pages load together, only once the list is open.
  const markedPage = useQuery({
    queryKey: ['not-counted', issue.id, 'false_positives'],
    queryFn: () => load(issue.id, 'false_positives', 0, FIRST),
    enabled: open && marked > 0,
  });
  const dismissedPage = useQuery({
    queryKey: ['not-counted', issue.id, 'dismissed'],
    queryFn: () => load(issue.id, 'dismissed', 0, FIRST),
    enabled: open && dismissed > 0,
  });
  if (!marked && !dismissed) return null;
  const loading =
    (marked > 0 && markedPage.isPending) || (dismissed > 0 && dismissedPage.isPending);
  const failed = markedPage.isError || dismissedPage.isError;
  return (
    <section ref={cardRef} className="rounded-xl border border-hairline bg-surface-1">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => {
          setOpen(!open);
          setConfirm(null);
        }}
        className="flex w-full items-center gap-3 rounded-xl border-0 bg-transparent px-6 py-5 text-left text-ink"
      >
        <h2 className="m-0 text-body font-medium">Not counted</h2>
        <span className="min-w-0 flex-1 text-label text-ink-muted">{notCountedSummary(issue)}</span>
        <ChevronRight
          className={cn(
            'size-4 flex-none text-ink-muted transition-transform',
            open && 'rotate-90'
          )}
          aria-hidden
        />
      </button>
      {open && (loading || failed) && (
        <div className="border-t border-hairline px-6 pt-3.5 pb-5 text-label text-ink-muted">
          {failed ? 'The list could not be loaded.' : 'Loading…'}
        </div>
      )}
      {open && !loading && !failed && (
        <>
          {markedPage.data && (
            <GroupRows
              issueId={issue.id}
              group="false_positives"
              title="Marked as false positives"
              page={markedPage.data}
              confirm={confirm}
              setConfirm={setConfirm}
            />
          )}
          {dismissedPage.data && (
            <GroupRows
              issueId={issue.id}
              group="dismissed"
              title="Dismissed by the model"
              page={dismissedPage.data}
              confirm={confirm}
              setConfirm={setConfirm}
            />
          )}
        </>
      )}
    </section>
  );
};
