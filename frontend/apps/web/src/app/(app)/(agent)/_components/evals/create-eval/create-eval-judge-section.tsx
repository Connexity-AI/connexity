'use client';
'use no memo';

import { useFormContext } from 'react-hook-form';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { cn } from '@workspace/ui/lib/utils';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import {
  EVAL_TIER_DOT,
  FieldLabel,
  Section,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-section-primitives';
import { useJudgeMetrics } from '@/app/(app)/(agent)/_components/evals/create-eval/use-judge-metrics';
import { useJudgeProvider } from '@/app/(app)/(agent)/_components/evals/create-eval/use-judge-provider';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { MetricDefinition, MetricTier } from '@/client/types.gen';

function ProviderAndModel() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const { providers, models, onProviderChange } = useJudgeProvider();

  return (
    <div className="grid grid-cols-2 gap-4">
      <FormField
        control={form.control}
        name="judge.provider"
        render={({ field }) => (
          <FormItem>
            <FieldLabel>LLM Provider</FieldLabel>

            <Select value={field.value} disabled={readOnly} onValueChange={onProviderChange}>
              <FormControl>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
              </FormControl>

              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.group} value={p.group}>
                    {p.group}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={form.control}
        name="judge.model"
        render={({ field }) => (
          <FormItem>
            <FieldLabel>LLM Model</FieldLabel>
            <Select value={field.value} onValueChange={field.onChange} disabled={readOnly}>
              <FormControl>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}

interface MetricsTableProps {
  metrics: MetricDefinition[];
}

function MetricsTable({ metrics }: MetricsTableProps) {
  const readOnly = useCreateEvalReadOnly();
  const { fields, rows, byName, enabledCount, allEnabled, toggleAll, updateRow, rootError } =
    useJudgeMetrics({ metrics });

  if (rows.length === 0) {
    return (
      <div className="rounded-md border border-border bg-accent/5 px-4 py-6 text-center text-xs text-muted-foreground/60">
        Loading metrics…
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-hidden rounded-md border border-border bg-accent/5">
        <div className="grid grid-cols-[24px_1fr_90px_72px] items-center gap-2 border-b border-border px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground/60">
          <Checkbox
            checked={allEnabled}
            disabled={readOnly}
            onCheckedChange={(checked) => toggleAll(Boolean(checked))}
            aria-label="Toggle all metrics"
          />
          <span>Metric</span>
          <span>Type</span>
          <span className="text-right">Weight</span>
        </div>
        <ul>
          {fields.map((field, index) => {
            const row = rows[index];
            if (!row) return null;
            const def = byName.get(row.metric);
            const tierDot = def ? EVAL_TIER_DOT[def.tier as MetricTier] : 'bg-muted';
            return (
              <li
                key={field.id}
                className={cn(
                  'grid grid-cols-[24px_1fr_90px_72px] items-center gap-2 border-b border-border/40 px-3 py-2 last:border-b-0',
                  !row.enabled && 'opacity-60'
                )}
              >
                <Checkbox
                  checked={row.enabled}
                  disabled={readOnly}
                  onCheckedChange={(checked) =>
                    updateRow(index, { ...row, enabled: Boolean(checked) })
                  }
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={cn('h-1.5 w-1.5 rounded-full', tierDot)} />
                    <span className="truncate text-sm">{def?.display_name ?? row.metric}</span>
                  </div>
                  {def ? (
                    <p className="mt-0.5 truncate text-[10px] text-muted-foreground/60">
                      {def.description}
                    </p>
                  ) : null}
                </div>
                <span className="text-[11px] text-muted-foreground">
                  {def?.score_type === 'binary' ? 'Binary' : 'Scored 0–5'}
                </span>
                <Input
                  type="number"
                  min={0}
                  max={10}
                  step={0.1}
                  disabled={!row.enabled || readOnly}
                  className="h-7 w-16 justify-self-end text-right font-mono text-xs"
                  value={row.weight}
                  onChange={(e) => {
                    const next = e.target.valueAsNumber;
                    updateRow(index, {
                      ...row,
                      weight: Number.isNaN(next) ? 0 : next,
                    });
                  }}
                />
              </li>
            );
          })}
        </ul>
      </div>
      <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground/50">
        <span>
          {enabledCount} / {rows.length} metrics enabled
        </span>
      </div>
      {typeof rootError === 'string' ? (
        <FormMessage className="mt-1.5">{rootError}</FormMessage>
      ) : null}
    </div>
  );
}

interface JudgeSectionProps {
  metrics: MetricDefinition[];
}

export function JudgeSection({ metrics }: JudgeSectionProps) {
  return (
    <Section>
      <Section.Header title="Judge" />
      <Section.Body>
        <div className="space-y-4">
          <ProviderAndModel />
          <MetricsTable metrics={metrics} />
        </div>
      </Section.Body>
    </Section>
  );
}
