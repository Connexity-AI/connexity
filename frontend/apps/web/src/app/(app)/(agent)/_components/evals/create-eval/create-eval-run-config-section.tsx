'use client';
'use no memo';

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
import { resolveRuntimeTestStatusMessage } from '@/app/(app)/(agent)/_components/evals/create-eval/runtime-test-status-message';
import { SubmittedCustomEndpointFieldFormMessage } from '@/app/(app)/(agent)/_components/evals/create-eval/submitted-custom-endpoint-field-form-message';
import { useRuntimeField } from '@/app/(app)/(agent)/_hooks/use-runtime-field';
import { useToolModeLiveGuard } from '@/app/(app)/(agent)/_hooks/use-tool-mode-live-guard';
import { runtimeIconForKind } from '@/app/(app)/(agent)/_utils/runtime-field-helpers';
import { missingLiveImplementations } from '@/app/(app)/(agent)/_utils/platform-live-tools-feasible';
import { AppModelsEnumsAgentMode, TextRuntimeKind } from '@/client/types.gen';

import type { CreateEvalFormValues } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { TextRuntimeKind as TextRuntimeKindType } from '@/client/types.gen';

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

  useToolModeLiveGuard(form, liveUnavailable);

  return (
    <FormField
      control={form.control}
      name="run.tool_mode"
      render={({ field }) => {
        const renderHint = () => {
          if (liveUnavailable) {
            return (
              <span className="text-amber-500/90">
                Live tool calls unavailable: add HTTP endpoint (or Python) under each platform tool
                ({missingImpl.join(', ')}) - or leave Mock selected.
              </span>
            );
          }

          if (field.value === 'mock') {
            return 'Tool responses are simulated using test case mock data';
          }

          if (agentMode !== AppModelsEnumsAgentMode.PLATFORM) {
            return 'Live applies to platform simulated agents only; endpoint agents ignore this setting.';
          }

          return 'Tools invoke stored implementations (HTTP / Python) during the eval run';
        };

        return (
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
            <FieldHint>{renderHint()}</FieldHint>
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
}

function RuntimeField({
  agentId,
  defaultToBackendOption,
}: {
  agentId: string;
  defaultToBackendOption: boolean;
}) {
  const {
    form,
    readOnly,
    error,
    isLoading,
    runtimeOptions,
    selectedRuntime,
    customEndpointUrl,
    testResult,
    testRuntime,
    selectRuntime,
    setCustomEndpointUrl,
    testCustomEndpoint,
    testDisabled,
  } = useRuntimeField({ agentId, defaultToBackendOption });

  return (
    <FormField
      control={form.control}
      name="run.runtime"
      render={({ field }) => (
        <FormItem className="col-span-2">
          <FieldLabel>Runtime</FieldLabel>

          {error ? (
            <FieldHint>Failed to load runtime options.</FieldHint>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {runtimeOptions.map((option) => {
                const Icon = runtimeIconForKind(option.kind);
                const active = field.value.kind === option.kind;
                return (
                  <button
                    key={option.kind}
                    type="button"
                    disabled={readOnly || isLoading}
                    onClick={() => selectRuntime(option.kind)}
                    className={cn(
                      'flex items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-all',
                      active ? 'border-foreground/40 bg-accent' : 'border-border bg-transparent',
                      !readOnly && !active && 'hover:bg-accent/40',
                      readOnly && 'cursor-default'
                    )}
                  >
                    <Icon
                      className={cn(
                        'mt-0.5 h-4 w-4 shrink-0',
                        active ? 'text-foreground' : 'text-muted-foreground'
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="text-xs text-foreground">{option.label}</p>
                        {option.is_default ? (
                          <span className="rounded bg-accent px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-muted-foreground">
                            Default
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-0.5 text-[10px] leading-tight text-muted-foreground">
                        {option.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {selectedRuntime.kind === TextRuntimeKind.CUSTOM_ENDPOINT ? (
            <div className="mt-4">
              <FieldLabel>Custom Endpoint URL</FieldLabel>
              <div className="flex items-start gap-2">
                <FormField
                  control={form.control}
                  name="run.runtime.url"
                  render={({ field: urlField, fieldState }) => (
                    <FormItem className="flex-1">
                      <FormControl>
                        <Input
                          value={customEndpointUrl}
                          onBlur={urlField.onBlur}
                          onChange={(e) => setCustomEndpointUrl(e.target.value)}
                          disabled={readOnly}
                          placeholder="https://your-agent.com/v1/chat/completions"
                          className="h-8 text-sm"
                        />
                      </FormControl>
                      <SubmittedCustomEndpointFieldFormMessage
                        isSubmitted={form.formState.isSubmitted}
                        message={fieldState.error?.message}
                      />
                    </FormItem>
                  )}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={testDisabled}
                  onClick={() => void testCustomEndpoint()}
                  className="h-8 shrink-0 text-xs"
                >
                  {testRuntime.isPending ? 'Testing...' : 'Test URL'}
                </Button>
              </div>
              <FieldHint>
                Connexity sends OpenAI-compatible chat completion requests to this endpoint
                during evals.
              </FieldHint>
              {testResult ? (
                <p
                  className={cn(
                    'mt-1 text-[11px]',
                    testResult.ok ? 'text-emerald-500' : 'text-destructive'
                  )}
                  role="status"
                >
                  {resolveRuntimeTestStatusMessage(testResult.message)}
                </p>
              ) : null}
            </div>
          ) : null}

          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function RunConfigToolModeSection({
  agentMode,
  agentTools,
  runtimeKind,
}: {
  agentMode: string | null;
  agentTools: unknown[] | null;
  runtimeKind: TextRuntimeKindType;
}) {
  const form = useFormContext<CreateEvalFormValues>();
  const isToolModeApplicable =
    agentMode === AppModelsEnumsAgentMode.PLATFORM &&
    runtimeKind === TextRuntimeKind.CONNEXITY;

  // keep persisted config aligned with backend behavior: tool mode only applies
  // to Connexity runtime on platform-mode agents.
  useToolModeLiveGuard(form, !isToolModeApplicable);

  if (!isToolModeApplicable) {
    return null;
  }

  return <ToolModeField agentMode={agentMode} agentTools={agentTools} />;
}

export function RunConfigSection() {
  return (
    <Section>
      <Section.Header title="Run Configuration" />
      <Section.Body>
        <div className="grid grid-cols-2 gap-4">
          <ConcurrencyField />

          <MaxTurnsField />
        </div>
      </Section.Body>
    </Section>
  );
}

interface RuntimeSectionProps {
  agentId: string;
  agentMode?: string | null;
  agentTools?: unknown[] | null;
  defaultToBackendOption?: boolean;
}

export function RuntimeSection({
  agentId,
  agentMode = null,
  agentTools = null,
  defaultToBackendOption = true,
}: RuntimeSectionProps) {
  const form = useFormContext<CreateEvalFormValues>();
  const runtimeKind = form.watch('run.runtime.kind');

  return (
    <Section>
      <Section.Header title="Runtime" />
      <Section.Body>
        <div className="grid grid-cols-2 gap-4">
          <RuntimeField
            agentId={agentId}
            defaultToBackendOption={defaultToBackendOption}
          />
          <RunConfigToolModeSection
            agentMode={agentMode}
            agentTools={agentTools}
            runtimeKind={runtimeKind}
          />
        </div>
      </Section.Body>
    </Section>
  );
}
