'use client';
'use no memo';

import { useFormContext, useWatch } from 'react-hook-form';

import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Slider } from '@workspace/ui/components/ui/slider';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import {
  FieldLabel,
  Section,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-section-primitives';
import { LlmModelPicker } from '@/app/(app)/(agent)/_components/llm/llm-model-picker';
import { temperatureLabel } from '@/app/(app)/(agent)/_constants/agent';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';

function ProviderAndModel() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const provider = useWatch({ control: form.control, name: 'persona.provider' });

  return (
    <div>
      <FormField
        control={form.control}
        name="persona.model"
        render={({ field }) => (
          <FormItem>
            <FieldLabel>LLM Model</FieldLabel>
            <LlmModelPicker
              value={field.value}
              provider={provider}
              onSelect={(modelOption) => {
                form.setValue('persona.provider', modelOption.provider, { shouldDirty: true });
                field.onChange(modelOption.model);
              }}
              disabled={readOnly}
            />
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}

function TemperatureField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  return (
    <FormField
      control={form.control}
      name="persona.temperature"
      render={({ field }) => (
        <FormItem>
          <div className="mb-1.5 flex items-center justify-between">
            <FieldLabel>Temperature</FieldLabel>
            <span className="font-mono text-xs tabular-nums text-muted-foreground">
              {temperatureLabel(field.value)} · {field.value.toFixed(1)}
            </span>
          </div>
          <FormControl>
            <Slider
              min={0}
              max={2}
              step={0.1}
              value={[field.value]}
              disabled={readOnly}
              onValueChange={(values) => field.onChange(values[0] ?? 0)}
            />
          </FormControl>

          <div className="mt-1 flex justify-between text-[10px] text-muted-foreground/50">
            <span>0.0</span>
            <span>1.0</span>
            <span>2.0</span>
          </div>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

export function PersonaSection() {
  return (
    <Section>
      <Section.Header title="Persona Simulation" />
      <Section.Body>
        <div className="space-y-4">
          <ProviderAndModel />
          <TemperatureField />
        </div>
      </Section.Body>
    </Section>
  );
}
