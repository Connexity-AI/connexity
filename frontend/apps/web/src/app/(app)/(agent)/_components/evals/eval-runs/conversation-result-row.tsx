'use client';

import { Check, X } from 'lucide-react';

import {
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@workspace/ui/components/ui/accordion';
import { cn } from '@workspace/ui/lib/utils';

import { ScoreBar } from './shared/score-bar';
import { roundScore, scoreColor } from './shared/score-utils';

import type { TestCaseResultPublic } from '@/client/types.gen';

type Verdict = NonNullable<TestCaseResultPublic['verdict']>;
type Outcome = NonNullable<Verdict['expected_outcome_results']>[number];
type Metric = NonNullable<Verdict['metric_scores']>[number];

interface ConversationResultRowProps {
  result: TestCaseResultPublic;
  testCaseName: string;
  onOpenTrace: () => void;
}

const TIER_COLORS: Record<string, string> = {
  execution: 'text-blue-400',
  knowledge: 'text-purple-400',
  process: 'text-amber-400',
  delivery: 'text-teal-400',
};

const isMetricPass = (m: Metric) => (m.is_binary ? m.score >= 5 : m.score >= 3);

export function ConversationResultRow({
  result,
  testCaseName,
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
          <ScoreBar value={score} />
        </div>
      </AccordionTrigger>

      <AccordionContent className="bg-background/50 px-5 pb-4 pt-0">
        <div className="flex flex-col gap-4 border-t border-border/40 pt-4">
          <OutcomesSection outcomes={outcomes} passedCount={passedOutcomes} />
          <MetricsSection metrics={metrics} passedCount={passedMetrics} />
        </div>
      </AccordionContent>
    </AccordionItem>
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
      className="rounded px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      Trace
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

function OutcomesSection({ outcomes, passedCount }: { outcomes: Outcome[]; passedCount: number }) {
  if (outcomes.length === 0) return null;

  return (
    <section className="flex flex-col gap-2">
      <h4 className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground/60">
        <span>Expected outcomes</span>
        <span>
          {passedCount}/{outcomes.length} passed
        </span>
      </h4>
      <ul className="flex flex-col gap-2">
        {outcomes.map((o, i) => (
          <OutcomeRow key={i} outcome={o} />
        ))}
      </ul>
    </section>
  );
}

function OutcomeRow({ outcome }: { outcome: Outcome }) {
  return (
    <li className="flex items-start gap-2 text-xs text-foreground">
      <StatusIcon passed={outcome.passed} className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <div className="min-w-0">
        <div>{outcome.statement}</div>
        <Justification text={outcome.justification} />
      </div>
    </li>
  );
}

function MetricsSection({ metrics, passedCount }: { metrics: Metric[]; passedCount: number }) {
  if (metrics.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h4 className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground/60">
        <span>Metrics</span>
        <span>
          {passedCount}/{metrics.length} passed
        </span>
      </h4>
      <ul className="flex flex-col gap-2">
        {metrics.map((m) => (
          <MetricRow key={m.metric} metric={m} />
        ))}
      </ul>
    </section>
  );
}

function MetricRow({ metric }: { metric: Metric }) {
  const isPass = isMetricPass(metric);
  return (
    <li className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="flex min-w-0 flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="truncate text-xs text-foreground">{metric.metric}</span>
          <MetricTier tier={metric.tier} />
        </div>
        <Justification text={metric.justification} className="mt-0 truncate" />
      </div>
      <div className="flex items-center gap-2">
        <MetricValue metric={metric} isPass={isPass} />
      </div>
    </li>
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
          'rounded-full border px-1.5 py-0.5 text-[10px]',
          isPass
            ? 'border-green-500/25 bg-green-500/15 text-green-400'
            : 'border-red-500/25 bg-red-500/15 text-red-400'
        )}
      >
        {isPass ? 'pass' : 'fail'}
      </span>
    );
  }
  return (
    <>
      <span
        className={cn(
          'font-mono text-[11px] tabular-nums',
          isPass ? 'text-foreground' : 'text-red-400'
        )}
      >
        {metric.score}/5
      </span>
      <ScoreBar value={(metric.score / 5) * 100} trackClassName="w-16" />
    </>
  );
}

function Justification({
  text,
  className,
}: {
  text: string | null | undefined;
  className?: string;
}) {
  if (!text) return null;
  return <div className={cn('mt-0.5 text-[11px] text-muted-foreground', className)}>{text}</div>;
}
