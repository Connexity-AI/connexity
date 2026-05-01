'use client';
'use no memo';

import { useEffect } from 'react';
import { useFormContext } from 'react-hook-form';

import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';
import { cn } from '@workspace/ui/lib/utils';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import {
  FieldHint,
  FieldLabel,
  Section,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-section-primitives';
import { missingLiveImplementations } from '@/app/(app)/(agent)/_utils/platform-live-tools-feasible';

import { AppModelsEnumsAgentMode } from '@/client/types.gen';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';

function ConcurrencyField() {
  const form = useFormContext<CreateEvalFormValues>();

  const readOnly = useCreateEvalReadOnly();
  return (
    <FormField
      control={form.control}
      name="run.concurrency"
      render={({ field }) => (
        <FormItem>
          <FieldLabel>Concurrency</FieldLabel>

          <FormControl>
            <Input
              type="number"
              min={1}
              max={50}
              className="h-9 text-sm"
              disabled={readOnly}
              {...field}
              value={field.value ?? ''}
              onChange={(e) => field.onChange(e.target.valueAsNumber)}
            />
          </FormControl>
          <FieldHint>Parallel scenarios at once</FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function MaxTurnsField() {
  const form = useFormContext<CreateEvalFormValues>();

  const readOnly = useCreateEvalReadOnly();

  return (
    <FormField
      control={form.control}
      name="run.max_turns"
      render={({ field }) => (
        <FormItem>
          <FieldLabel>Max turns per test case</FieldLabel>

          <FormControl>
            <Input
              type="number"
              min={1}
              max={200}
              placeholder="No limit"
              className="h-9 text-sm"
              disabled={readOnly}
              value={field.value ?? ''}
              onChange={(e) => {
                const v = e.target.value;
                field.onChange(v === '' ? null : Number(v));
              }}
            />
          </FormControl>
          <FieldHint>Leave blank for no cap on agent response rounds</FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

const TOOL_MODES = ['mock', 'live'] as const;

interface ToolModeFieldProps {
  agentMode: string | null;
  agentTools: unknown[] | null;
}

function ToolModeField({ agentMode, agentTools }: ToolModeFieldProps) {
  const form = useFormContext<CreateEvalFormValues>();

  const readOnly = useCreateEvalReadOnly();

  const isPlatform = agentMode === AppModelsEnumsAgentMode.PLATFORM;
  const missingImpl = isPlatform ? missingLiveImplementations(agentTools ?? undefined) : [];
  const liveUnavailable = isPlatform && missingImpl.length > 0;

  const toolMode = form.watch('run.tool_mode');

  useEffect(() => {
    if (liveUnavailable && toolMode === 'live') {
      form.setValue('run.tool_mode', 'mock', { shouldValidate: true, shouldDirty: true });
    }
  }, [liveUnavailable, toolMode, form]);

  return (
    <FormField
      control={form.control}
      name="run.tool_mode"
      render={({ field }) => (
        <FormItem className="col-span-2">
          <FieldLabel>Tool Calls</FieldLabel>

          <div className="flex items-center gap-1 p-0.5 rounded-lg border border-border bg-accent/20 w-fit">
            {TOOL_MODES.map((mode) => {
              const selected = field.value === mode;
              const liveDisabled = readOnly || (mode === 'live' && liveUnavailable);
              return (
                <button
                  key={mode}
                  type="button"
                  disabled={liveDisabled}
                  title={
                    mode === 'live' && liveUnavailable
                      ? `Add live webhook or Python implementations for: ${missingImpl.join(', ')}`
                      : undefined
                  }
                  onClick={() => field.onChange(mode)}
                  className={cn(
                    'px-4 py-1.5 rounded-md text-xs transition-all capitalize',
                    selected
                      ? mode === 'live'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 shadow-sm'
                        : 'bg-accent text-foreground border border-border shadow-sm'
                      : 'text-muted-foreground hover:text-foreground',
                    liveDisabled && 'cursor-not-allowed opacity-60'
                  )}
                >
                  {mode === 'live' && (
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1.5 align-middle" />
                  )}
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </button>
              );
            })}
          </div>
          <FieldHint>
            {liveUnavailable ? (
              <span className="text-amber-500/90">
                Live tool calls unavailable: add HTTP endpoint (or Python) under each platform
                tool ({missingImpl.join(', ')}) — or leave Mock selected.
              </span>
            ) : field.value === 'mock' ? (
              'Tool responses are simulated using test case mock data'
            ) : agentMode !== AppModelsEnumsAgentMode.PLATFORM ? (
              'Live applies to platform simulated agents only; endpoint agents ignore this setting.'
            ) : (
              'Tools invoke stored implementations (HTTP / Python) during the eval run'
            )}
          </FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

interface RunConfigSectionProps {
  agentMode?: string | null;
  agentTools?: unknown[] | null;
}

export function RunConfigSection({ agentMode = null, agentTools = null }: RunConfigSectionProps) {
  return (
    <Section>
      <Section.Header title="Run Configuration" />
      <Section.Body>
        <div className="grid grid-cols-2 gap-4">
          <ConcurrencyField />
          <MaxTurnsField />
          <ToolModeField agentMode={agentMode} agentTools={agentTools} />
        </div>
      </Section.Body>
    </Section>
  );
}
