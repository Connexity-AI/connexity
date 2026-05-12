'use client';
'use no memo';

import { useEffect } from 'react';

import { Bot, FlaskConical } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
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
type ToolMode = (typeof TOOL_MODES)[number];

interface ToolModeToggleButtonProps {
  mode: ToolMode;
  selected: boolean;
  liveDisabled: boolean;
  liveUnavailable: boolean;
  missingImpl: string[];
  onSelect: (mode: ToolMode) => void;
}

function ToolModeToggleButton({
  mode,
  selected,
  liveDisabled,
  liveUnavailable,
  missingImpl,
  onSelect,
}: ToolModeToggleButtonProps) {
  const baseClassName = 'px-4 py-1.5 rounded-md text-xs transition-all capitalize';

  const buildClassName = () => {
    if (selected && mode === 'live') {
      return cn(
        baseClassName,
        'bg-amber-500/20 text-amber-400 border border-amber-500/30 shadow-sm',
        liveDisabled && 'cursor-not-allowed opacity-60'
      );
    }

    if (selected) {
      return cn(
        baseClassName,
        'bg-accent text-foreground border border-border shadow-sm',
        liveDisabled && 'cursor-not-allowed opacity-60'
      );
    }

    return cn(
      baseClassName,
      'text-muted-foreground hover:text-foreground',
      liveDisabled && 'cursor-not-allowed opacity-60'
    );
  };

  const buildTitle = () => {
    if (mode === 'live' && liveUnavailable) {
      return `Add live webhook or Python implementations for: ${missingImpl.join(', ')}`;
    }

    return undefined;
  };

  const renderLiveDot = () => {
    if (mode !== 'live') {
      return null;
    }

    return (
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1.5 align-middle" />
    );
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      disabled={liveDisabled}
      title={buildTitle()}
      onClick={() => onSelect(mode)}
      className={buildClassName()}
    >
      {renderLiveDot()}
      {mode.charAt(0).toUpperCase() + mode.slice(1)}
    </Button>
  );
}

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
                <ToolModeToggleButton
                  key={mode}
                  mode={mode}
                  selected={selected}
                  liveDisabled={liveDisabled}
                  liveUnavailable={liveUnavailable}
                  missingImpl={missingImpl}
                  onSelect={field.onChange}
                />
              );
            })}
          </div>
          <FieldHint>
            {liveUnavailable ? (
              <span className="text-amber-500/90">
                Live tool calls unavailable: add HTTP endpoint (or Python) under each platform tool
                ({missingImpl.join(', ')}) — or leave Mock selected.
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

function EvaluationEngineField({
  agentMode,
  endpointUrl,
}: {
  agentMode: string | null;
  endpointUrl: string | null;
}) {
  const evalEngine = agentMode === AppModelsEnumsAgentMode.ENDPOINT ? 'agent' : 'connexity';

  const cards = [
    {
      value: 'connexity',
      label: 'Connexity',
      description: 'Run evaluations using Connexity',
      icon: FlaskConical,
    },
    {
      value: 'agent',
      label: 'Your Agent',
      description: 'Run evaluations against your own agent',
      icon: Bot,
    },
  ] as const;

  return (
    <div className="col-span-2">
      <FieldLabel>Evaluation Engine</FieldLabel>
      <div className="grid grid-cols-1 gap-2">
        {cards.map((card) => {
          const Icon = card.icon;
          const active = evalEngine === card.value;
          return (
            <button
              key={card.value}
              type="button"
              disabled
              className={cn(
                'flex cursor-default items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-all',
                active ? 'border-foreground/40 bg-accent' : 'border-border bg-transparent'
              )}
            >
              <Icon
                className={cn(
                  'mt-0.5 h-4 w-4 shrink-0',
                  active ? 'text-foreground' : 'text-muted-foreground'
                )}
              />
              <div className="min-w-0 flex-1">
                <p className="text-xs text-foreground">{card.label}</p>
                <p className="mt-0.5 text-[10px] leading-tight text-muted-foreground">
                  {card.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
      {evalEngine === 'agent' ? (
        <div className="mt-4">
          <FieldLabel>Chat completions URL</FieldLabel>
          <Input
            value={endpointUrl ?? ''}
            readOnly
            disabled
            placeholder="https://your-agent.com/v1/chat/completions"
            className="h-8 text-sm"
          />
          <FieldHint>
            Connexity sends OpenAI-compatible chat completion requests to this endpoint during
            evals.
          </FieldHint>
        </div>
      ) : null}
    </div>
  );
}

interface RunConfigSectionProps {
  agentMode?: string | null;
  agentTools?: unknown[] | null;
  endpointUrl?: string | null;
}

function RunConfigToolModeSection({
  agentMode,
  agentTools,
}: {
  agentMode: string | null;
  agentTools: unknown[] | null;
}) {
  if (agentMode !== AppModelsEnumsAgentMode.PLATFORM) {
    return null;
  }

  return <ToolModeField agentMode={agentMode} agentTools={agentTools} />;
}

export function RunConfigSection({
  agentMode = null,
  agentTools = null,
  endpointUrl = null,
}: RunConfigSectionProps) {
  return (
    <Section>
      <Section.Header title="Run Configuration" />
      <Section.Body>
        <div className="grid grid-cols-2 gap-4">
          <ConcurrencyField />

          <MaxTurnsField />

          <EvaluationEngineField agentMode={agentMode} endpointUrl={endpointUrl ?? ''} />

          <RunConfigToolModeSection agentMode={agentMode} agentTools={agentTools} />
        </div>
      </Section.Body>
    </Section>
  );
}
