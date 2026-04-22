'use client';

import { Check, MessageSquare, X } from 'lucide-react';

import {
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@workspace/ui/components/ui/accordion';
import { cn } from '@workspace/ui/lib/utils';

import { roundScore, scoreColor } from './shared/score-utils';

import type { Difficulty, TestCaseResultPublic } from '@/client/types.gen';

type Verdict = NonNullable<TestCaseResultPublic['verdict']>;
type Outcome = NonNullable<Verdict['expected_outcome_results']>[number];
type Metric = NonNullable<Verdict['metric_scores']>[number];

interface ConversationResultRowProps {
  result: TestCaseResultPublic;
  testCaseName: string;
  tags?: string[];
  difficulty?: Difficulty;
  onOpenTrace: () => void;
}

const TIER_COLORS: Record<string, string> = {
  execution: 'text-blue-400',
  knowledge: 'text-purple-400',
  process: 'text-amber-400',
  delivery: 'text-teal-400',
};

const DIFFICULTY_COLORS: Record<Difficulty, string> = {
  normal: 'bg-accent/60 text-muted-foreground',
  hard: 'bg-amber-500/15 text-amber-400',
};

const isMetricPass = (m: Metric) => (m.is_binary ? m.score >= 5 : m.score >= 3);

export function ConversationResultRow({
  result,
  testCaseName,
  tags,
  difficulty,
  onOpenTrace,
}: ConversationResultRowProps) {
  const verdict = result.verdict;
  const score = roundScore(verdict?.overall_score);
  const scoreColors = scoreColor(score);
  const outcomes = verdict?.expected_outcome_results ?? [];
  const metrics = verdict?.metric_scores ?? [];
  const passedOutcomes = outcomes.filter((o) => o.passed).length;
  const passedMetrics = metrics.filter(isMetricPass).length;

  return (
    <AccordionItem value={result.id} className="border-b border-border/40 last:border-b-0">
      <AccordionTrigger
        className={cn(
          'grid grid-cols-[24px_1fr_auto_auto_auto_auto] items-center gap-3 px-5 py-3',
          'font-normal text-foreground hover:no-underline',
          'hover:bg-accent/20 data-[state=open]:bg-accent/30'
        )}
      >
        <div className="flex h-6 w-6 items-center justify-center">
          <StatusIcon passed={result.passed} className="h-4 w-4" />
        </div>

        <div className="min-w-0 text-left">
          <div className="truncate text-sm text-foreground">{testCaseName}</div>
          <TagRow tags={tags} difficulty={difficulty} />
          <ErrorMessage message={result.error_message} />
        </div>

        <div className="flex items-center gap-1" aria-label="Outcomes">
          {outcomes.slice(0, 6).map((o, i) => (
            <span
              key={i}
              className={cn('h-1.5 w-1.5 rounded-full', o.passed ? 'bg-green-400' : 'bg-red-400')}
            />
          ))}
          <OutcomesOverflow total={outcomes.length} />
        </div>

        <TraceAction onOpenTrace={onOpenTrace} />

        <div className="flex w-[110px] flex-col items-end gap-1">
          <span className={cn('font-mono text-xs tabular-nums', scoreColors.text)}>
            {score === null ? '—' : `${score}/100`}
          </span>
          <ScoreBarInline value={score} />
        </div>
      </AccordionTrigger>

      <AccordionContent className="p-0">
        <div className="border-t border-border/40">
          <OutcomesSection outcomes={outcomes} passedCount={passedOutcomes} />
          <MetricsSection metrics={metrics} passedCount={passedMetrics} />
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

function TagRow({ tags, difficulty }: { tags?: string[]; difficulty?: Difficulty }) {
  const hasTags = tags && tags.length > 0;
  if (!difficulty && !hasTags) return null;
  return (
    <div className="mt-1 flex flex-wrap items-center gap-1.5">
      {difficulty ? <DifficultyBadge difficulty={difficulty} /> : null}
      {hasTags
        ? tags!.map((tag) => (
            <span
              key={tag}
              className="rounded bg-accent px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
              {tag}
            </span>
          ))
        : null}
    </div>
  );
}

function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  return (
    <span
      className={cn(
        'rounded px-1.5 py-0.5 text-[10px] capitalize',
        DIFFICULTY_COLORS[difficulty]
      )}
    >
      {difficulty}
    </span>
  );
}

function TraceAction({ onOpenTrace }: { onOpenTrace: () => void }) {
  const handle = (e: React.SyntheticEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onOpenTrace();
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handle}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') handle(e);
      }}
      className="flex items-center gap-1.5 rounded border border-transparent px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:border-border hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <MessageSquare className="h-3.5 w-3.5" />
      <span>Trace</span>
    </div>
  );
}

function ScoreBarInline({ value }: { value: number | null }) {
  const pct = Math.max(0, Math.min(100, value ?? 0));
  const color = scoreColor(value).bar;
  return (
    <div className="h-1.5 w-[110px] overflow-hidden rounded-full bg-accent/80">
      <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

function StatusIcon({
  passed,
  className,
}: {
  passed: boolean | null | undefined;
  className?: string;
}) {
  if (passed) return <Check className={cn('text-green-400', className)} />;
  return <X className={cn('text-red-400', className)} />;
}

function ErrorMessage({ message }: { message: string | null | undefined }) {
  if (!message) return null;
  return <div className="mt-0.5 truncate text-[11px] text-red-400/80">{message}</div>;
}

function OutcomesOverflow({ total }: { total: number }) {
  if (total <= 6) return null;
  return <span className="text-[10px] text-muted-foreground">+{total - 6}</span>;
}

function SectionHeader({
  title,
  passedCount,
  total,
}: {
  title: string;
  passedCount: number;
  total: number;
}) {
  return (
    <div className="flex items-center gap-2 border-y border-border/30 bg-accent/5 px-8 py-1.5">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50">{title}</span>
      <span className="ml-auto text-[10px] tabular-nums text-muted-foreground/40">
        {passedCount}/{total} passed
      </span>
    </div>
  );
}

function OutcomesSection({ outcomes, passedCount }: { outcomes: Outcome[]; passedCount: number }) {
  if (outcomes.length === 0) return null;

  return (
    <section>
      <SectionHeader title="Expected Outcomes" passedCount={passedCount} total={outcomes.length} />
      {outcomes.map((o, i) => (
        <OutcomeRow key={i} outcome={o} />
      ))}
    </section>
  );
}

function OutcomeRow({ outcome }: { outcome: Outcome }) {
  return (
    <div className="flex items-start gap-3 border-b border-border/20 bg-background px-8 py-3 last:border-0">
      <div
        className={cn(
          'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full',
          outcome.passed ? 'bg-green-500/15' : 'bg-red-500/15'
        )}
      >
        {outcome.passed ? (
          <Check className="h-2.5 w-2.5 text-green-400" />
        ) : (
          <X className="h-2.5 w-2.5 text-red-400" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            'text-xs leading-relaxed',
            outcome.passed ? 'text-foreground' : 'text-muted-foreground'
          )}
        >
          {outcome.statement}
        </p>
        {outcome.justification ? (
          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground/70">
            {outcome.justification}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function MetricsSection({ metrics, passedCount }: { metrics: Metric[]; passedCount: number }) {
  if (metrics.length === 0) return null;
  return (
    <section>
      <SectionHeader title="Metrics" passedCount={passedCount} total={metrics.length} />
      {metrics.map((m) => (
        <MetricRow key={m.metric} metric={m} />
      ))}
    </section>
  );
}

function MetricRow({ metric }: { metric: Metric }) {
  const isPass = isMetricPass(metric);
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-6 border-b border-border/20 bg-background px-8 py-3 last:border-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-xs text-foreground">{humanizeMetricName(metric.metric)}</p>
          <MetricTier tier={metric.tier} />
        </div>
        {metric.justification ? (
          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground/70">
            ↳ {metric.justification}
          </p>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2.5">
        <MetricValue metric={metric} isPass={isPass} />
      </div>
    </div>
  );
}

function MetricTier({ tier }: { tier: Metric['tier'] }) {
  if (!tier) return null;
  const tierColor = TIER_COLORS[tier];
  return (
    <span
      className={cn('text-[10px] uppercase tracking-wider', tierColor ?? 'text-muted-foreground')}
    >
      {tier}
    </span>
  );
}

function MetricValue({ metric, isPass }: { metric: Metric; isPass: boolean }) {
  if (metric.is_binary) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 rounded px-2.5 py-1 text-[10px]',
          isPass ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
        )}
      >
        {isPass ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
        {isPass ? 'Pass' : 'Fail'}
      </span>
    );
  }
  const pct = (metric.score / 5) * 100;
  const colorClass =
    metric.score >= 4 ? 'text-green-400' : metric.score === 3 ? 'text-yellow-400' : 'text-red-400';
  const barClass =
    metric.score >= 4 ? 'bg-green-400' : metric.score === 3 ? 'bg-yellow-400' : 'bg-red-400';
  return (
    <>
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-accent/80">
        <div className={cn('h-full rounded-full', barClass)} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn('w-8 text-right font-mono text-xs tabular-nums', colorClass)}>
        {metric.score}/5
      </span>
    </>
  );
}

function humanizeMetricName(slug: string): string {
  return slug
    .split('_')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
