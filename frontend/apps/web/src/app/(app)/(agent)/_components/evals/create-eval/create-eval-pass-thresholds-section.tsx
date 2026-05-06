'use client';
'use no memo';

import { ListChecks, Target } from 'lucide-react';
import { useFormContext, useWatch } from 'react-hook-form';

import { Slider } from '@workspace/ui/components/ui/slider';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import {
  FieldLabel,
  Section,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-section-primitives';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';

export function PassThresholdsSection() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();

  const metricsPct = useWatch({ control: form.control, name: 'run.metrics_pass_threshold' });
  const casesPct = useWatch({ control: form.control, name: 'run.cases_pass_threshold' });

  return (
    <Section>
      <Section.Header title="Pass Thresholds" />
      <Section.Body>
        <div className="space-y-5">
          <div>
            <div className="flex items-center justify-between mb-2">
              <FieldLabel>Metrics pass rate</FieldLabel>
              <span className="text-xs font-mono text-emerald-400 tabular-nums inline-flex items-center gap-1">
                <Target className="w-3 h-3" />
                {metricsPct}%
              </span>
            </div>
            <Slider
              min={0}
              max={100}
              step={1}
              value={[metricsPct]}
              disabled={readOnly}
              onValueChange={([v]) =>
                form.setValue('run.metrics_pass_threshold', v ?? 0, {
                  shouldDirty: true,
                  shouldValidate: true,
                })
              }
            />
            <p className="text-[10px] text-muted-foreground/40 mt-1.5">
              Required average score across enabled metrics
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <FieldLabel>Test cases pass rate</FieldLabel>
              <span className="text-xs font-mono text-emerald-400 tabular-nums inline-flex items-center gap-1">
                <ListChecks className="w-3 h-3" />
                {casesPct}%
              </span>
            </div>
            <Slider
              min={0}
              max={100}
              step={1}
              value={[casesPct]}
              disabled={readOnly}
              onValueChange={([v]) =>
                form.setValue('run.cases_pass_threshold', v ?? 0, {
                  shouldDirty: true,
                  shouldValidate: true,
                })
              }
            />
            <p className="text-[10px] text-muted-foreground/40 mt-1.5">
              Required share of test cases meeting their expected outcomes
            </p>
          </div>
        </div>
      </Section.Body>
    </Section>
  );
}
