'use client';

import { useState } from 'react';
import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import {
  ChevronDown,
  ChevronRight,
  CircleCheck,
  CircleX,
  FileText,
  GitCompare,
  OctagonAlert,
  TriangleAlert,
} from 'lucide-react';

import { NumberTile } from '@workspace/ui/components/number-tile';
import { cn } from '@workspace/ui/lib/utils';

import { parseTime } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';

import type { SpecGroupPublic, SpecPublic, SpecRulePublic } from '@/client/types.gen';
import type { Route } from 'next';
import type { FC, ReactNode } from 'react';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const TOUCHES: Record<string, [string, string]> = {
  money: ['Money', 'Touches money'],
  safety: ['Safety', 'Touches caller safety'],
  compliance: ['Compliance', 'Touches compliance'],
};

/** "6 Nov" in the viewer's time zone. */
const dayLabel = (iso: string) => {
  const date = parseTime(iso);
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
};

const source = (rule: SpecRulePublic) => {
  if (rule.source !== 'clarification') return 'From the prompt';
  const who = rule.answered_by ? ` answered by ${rule.answered_by}` : '';
  const when = rule.answered_at ? ` on ${dayLabel(rule.answered_at)}` : '';
  return `From a clarification,${who}${when}`.replace(/,$/, '');
};

/** In conflict first, then rules that touch money, safety or compliance, then the spec's order. */
const rank = (rule: SpecRulePublic) => (rule.in_conflict ? 0 : rule.touches ? 1 : 2);

const Badge: FC<{
  tone: 'critical' | 'warning' | 'passed' | 'plain';
  children: ReactNode;
  className?: string;
}> = ({ tone, children, className }) => (
  <span
    className={cn(
      'inline-flex h-[22px] flex-none items-center gap-1 rounded-md px-1.5 text-label font-medium',
      tone === 'critical' && 'bg-critical-bg text-critical',
      tone === 'warning' && 'bg-warning-bg text-warning',
      tone === 'passed' && 'bg-passed-bg text-passed',
      tone === 'plain' && 'border border-border-control text-ink-secondary',
      className
    )}
  >
    {children}
  </span>
);

/** The rule's result in the live version's latest full run. */
const Mark: FC<{ result: SpecRulePublic['result'] }> = ({ result }) => {
  if (!result) return null;
  return (
    <span className="flex w-[148px] items-center gap-1.5 text-label whitespace-nowrap">
      {result === 'passed' && (
        <span className="inline-flex items-center gap-1.5 text-passed">
          <CircleCheck className="size-3.5" aria-hidden />
          Passed
        </span>
      )}
      {result === 'failed' && (
        <span className="inline-flex items-center gap-1.5 font-medium text-critical">
          <CircleX className="size-3.5" aria-hidden />
          Failed
        </span>
      )}
      {result === 'flaky' && (
        <span className="inline-flex h-5 items-center rounded-md bg-warning-bg px-1.5 font-medium text-warning">
          Flaky
        </span>
      )}
      {result === 'did_not_come_up' && <span className="text-ink-muted">Didn’t come up</span>}
      {result === 'no_scenario' && <span className="text-ink-muted">No scenario</span>}
    </span>
  );
};

const RuleRow: FC<{ rule: SpecRulePublic; questionsHref: Route }> = ({ rule, questionsHref }) => {
  const dropped = rule.change === 'dropped';
  const touches = rule.touches ? TOUCHES[rule.touches] : undefined;
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 py-[7px] pr-6 pl-12 hover:bg-wash">
      <div className="flex min-w-0 flex-col">
        <div className="flex flex-wrap items-center gap-2">
          {rule.critical && (
            <Badge tone="critical" className="px-2">
              <OctagonAlert className="size-3.5" aria-hidden />
              Critical
            </Badge>
          )}
          <span className={cn('text-pretty', dropped && 'text-ink-muted line-through')}>
            {rule.text}
          </span>
          {touches && (
            <span
              title={touches[1]}
              className="inline-flex h-5 items-center rounded-md bg-unchecked-bg px-1.5 text-label font-medium text-unchecked"
            >
              {touches[0]}
            </span>
          )}
        </div>
        <span className="text-label text-ink-muted">
          {source(rule)}
          {rule.in_conflict && (
            <span className="text-warning">
              {' '}
              · The new prompt says otherwise.{' '}
              <Link href={questionsHref} className="text-warning">
                Open the clarification
              </Link>
            </span>
          )}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        {rule.change === 'added' && <Badge tone="passed">Added</Badge>}
        {dropped && <Badge tone="plain">Dropped</Badge>}
        {rule.in_conflict && (
          <Badge tone="warning">
            <TriangleAlert className="size-3.5" aria-hidden />
            In conflict
          </Badge>
        )}
        <Mark result={rule.result} />
      </div>
    </div>
  );
};

const Group: FC<{ group: SpecGroupPublic; changesOnly: boolean; questionsHref: Route }> = ({
  group,
  changesOnly,
  questionsHref,
}) => {
  const [open, setOpen] = useState(false);
  const rules = (changesOnly ? group.rules.filter((r) => r.change !== 'kept') : group.rules)
    .map((rule, i) => ({ rule, i }))
    .sort((a, b) => rank(a.rule) - rank(b.rule) || a.i - b.i)
    .map(({ rule }) => rule);
  if (rules.length === 0) return null;
  const critical = rules.filter((r) => r.critical).length;
  const conflicts = rules.filter((r) => r.in_conflict).length;
  const added = rules.filter((r) => r.change === 'added').length;
  const dropped = rules.filter((r) => r.change === 'dropped').length;
  const failed = rules.filter((r) => r.result === 'failed' || r.result === 'flaky').length;
  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <div className="border-t border-hairline">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex min-h-12 w-full items-center gap-2 border-0 bg-transparent px-6 text-left text-body text-ink hover:bg-wash"
      >
        <Chevron className="size-4 flex-none text-ink-secondary" aria-hidden />
        <span>{group.name}</span>
        <span className="text-label text-ink-secondary">{rules.length}</span>
        {critical > 0 && (
          <Badge tone="critical">
            <OctagonAlert className="size-3.5" aria-hidden />
            {critical} critical
          </Badge>
        )}
        {conflicts > 0 && (
          <Badge tone="warning">
            <TriangleAlert className="size-3.5" aria-hidden />
            {conflicts} in conflict
          </Badge>
        )}
        {added > 0 && <Badge tone="passed">{added} added</Badge>}
        {dropped > 0 && <Badge tone="plain">{dropped} dropped</Badge>}
        {failed > 0 && (
          <span className="inline-flex h-[22px] flex-none items-center gap-1 text-label font-medium text-critical">
            <CircleX className="size-3.5" aria-hidden />
            {failed} failed
          </span>
        )}
      </button>
      {open && (
        <div className="pb-2">
          {rules.map((rule) => (
            <RuleRow
              key={`${rule.key}-${rule.change ?? ''}`}
              rule={rule}
              questionsHref={questionsHref}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface Props {
  spec: SpecPublic;
  /** When the agent version went live, for the version line. */
  liveSince?: string | null;
  onCompare: (version: string | undefined) => void;
}

/**
 * The Spec tab (designs/screens/Connexity Agent Profile.dc.html; plans/2026-11-15-spec-tab.md):
 * read only. The open-clarifications tile and "In conflict" open the questions on Work.
 */
export const SpecTab: FC<Props> = ({ spec, liveSince, onCompare }) => {
  const [changesOnly, setChangesOnly] = useState(false);
  const version = spec.spec;

  if (!version) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-hairline bg-surface-1 px-6 py-10 text-center">
        <FileText className="size-5 text-ink-muted" aria-hidden />
        <p className="m-0 max-w-[520px] text-pretty text-ink-secondary">
          No spec yet. Your assistant writes it from the agent&apos;s prompt.
        </p>
      </div>
    );
  }

  const comparison = spec.comparison;
  const counts = spec.counts;
  const conflicts = counts?.in_conflict ?? 0;
  const earlier = (spec.versions ?? []).filter((v) => v.version !== version.version);
  const options = [
    { value: 'none', label: `Version ${version.version} only` },
    ...earlier.map((v) => ({
      value: String(v.version),
      label: `Compare with version ${v.version}`,
    })),
  ];
  const since =
    version.agent_version === spec.current_agent_version && liveSince
      ? `, since ${dayLabel(liveSince)}`
      : '';

  return (
    <div className="flex flex-col gap-4">
      {comparison ? (
        <div className="grid grid-cols-5 gap-3">
          <NumberTile label="Kept" value={comparison.kept.toLocaleString()} />
          <NumberTile label="Added" value={comparison.added.toLocaleString()} />
          <NumberTile label="Dropped" value={comparison.dropped.toLocaleString()} />
        </div>
      ) : (
        <div className="grid grid-cols-5 gap-3">
          <NumberTile label="Rules" value={version.rule_count.toLocaleString()} />
          <NumberTile label="From the prompt" value={(counts?.from_prompt ?? 0).toLocaleString()} />
          <NumberTile
            label="From clarifications"
            value={(counts?.from_clarifications ?? 0).toLocaleString()}
          />
          <NumberTile
            label="In conflict"
            value={conflicts.toLocaleString()}
            severity={conflicts > 0 ? 'warning' : undefined}
          />
          <Link
            href={UrlGenerator.work(spec.agent_id)}
            title="Answer on Work"
            className="rounded-xl text-ink no-underline hover:opacity-90"
          >
            <NumberTile
              label="Open clarifications"
              value={(spec.open_clarifications ?? 0).toLocaleString()}
            />
          </Link>
        </div>
      )}

      <section className="rounded-xl border border-hairline bg-surface-1">
        <div className="flex items-center justify-between gap-4 px-6 py-4">
          <div className="flex min-w-0 flex-col gap-0.5">
            <h2 className="m-0 text-body font-medium">
              Version {version.version}
              <span className="font-normal text-ink-muted">
                {' '}
                · agent version {version.agent_version}
                {since}
              </span>
            </h2>
            {version.version === spec.latest_version && (
              <span className="text-label text-ink-muted">
                {spec.results_at
                  ? `Results from the full run of ${dayLabel(spec.results_at)}`
                  : `No full run on ${spec.results_version ? `version ${spec.results_version}` : 'the live version'} yet`}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {comparison && (
              <button
                type="button"
                role="switch"
                aria-checked={changesOnly}
                onClick={() => setChangesOnly(!changesOnly)}
                className="flex h-9 items-center gap-2 border-0 bg-transparent p-0 text-label text-ink-secondary"
              >
                <span
                  className={cn(
                    'relative h-5 w-9 rounded-full transition-colors',
                    changesOnly ? 'bg-ink' : 'bg-border-control'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 size-4 rounded-full bg-surface-1 transition-all',
                      changesOnly ? 'left-[18px]' : 'left-0.5'
                    )}
                  />
                </span>
                Show changes only
              </button>
            )}
            {earlier.length > 0 && (
              <Picker
                label={
                  comparison
                    ? `Compared with version ${comparison.version}`
                    : 'Compare with an earlier version'
                }
                value={undefined}
                highlighted={Boolean(comparison)}
                options={options}
                onPick={(value) => onCompare(value && value !== 'none' ? value : undefined)}
                icon={<GitCompare className="size-4 text-ink-secondary" aria-hidden />}
                align="end"
                clearable={false}
              />
            )}
          </div>
        </div>
        {(spec.groups ?? []).map((group) => (
          <Group
            key={group.category}
            group={group}
            changesOnly={changesOnly}
            questionsHref={UrlGenerator.work(spec.agent_id)}
          />
        ))}
      </section>
    </div>
  );
};
