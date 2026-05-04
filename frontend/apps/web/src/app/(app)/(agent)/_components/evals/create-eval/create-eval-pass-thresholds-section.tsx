'use client';
'use no memo';

import { useFormContext } from 'react-hook-form';

import { FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Slider } from '@workspace/ui/components/ui/slider';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import {
  FieldHint,
  FieldLabel,
  Section,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-section-primitives';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';

function MetricsThresholdField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();

  return (
    <FormField
      control={form.control}
      name="thresholds.metrics_pass_threshold"
      render={({ field }) => (
        <FormItem>
          <div className="mb-2 flex items-center justify-between">
            <FieldLabel>Metrics pass rate</FieldLabel>
            <span className="font-mono text-xs tabular-nums text-violet-400">
              {field.value}%
            </span>
          </div>
          <Slider
            min={0}
            max={100}
            step={1}
            value={[field.value]}
            onValueChange={([v]) => field.onChange(v)}
            disabled={readOnly}
          />
          <FieldHint>Required average score across enabled metrics</FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function CasesThresholdField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();

  return (
    <FormField
      control={form.control}
      name="thresholds.cases_pass_threshold"
      render={({ field }) => (
        <FormItem>
          <div className="mb-2 flex items-center justify-between">
            <FieldLabel>Test cases pass rate</FieldLabel>
            <span className="font-mono text-xs tabular-nums text-emerald-400">
              {field.value}%
            </span>
          </div>
          <Slider
            min={0}
            max={100}
            step={1}
            value={[field.value]}
            onValueChange={([v]) => field.onChange(v)}
            disabled={readOnly}
          />
          <FieldHint>
            Required share of test cases meeting their expected outcomes
          </FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

export function PassThresholdsSection() {
  return (
    <Section>
      <Section.Header title="Pass Thresholds" />
      <Section.Body>
        <div className="space-y-5">
          <MetricsThresholdField />
          <CasesThresholdField />
        </div>
      </Section.Body>
    </Section>
  );
}
