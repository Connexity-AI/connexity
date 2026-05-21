'use client';
'use no memo';

import type { ReactNode } from 'react';

import { useFormContext } from 'react-hook-form';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@workspace/ui/components/ui/button';
import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@workspace/ui/components/ui/tooltip';
import { cn } from '@workspace/ui/lib/utils';

import { agentDetailQuery } from '@/app/(app)/(agent)/_queries/agent-detail-query';
import { appConfigQueries } from '@/app/(app)/(agent)/_queries/app-config-query';
import { getPublicEnv } from '@/config/process-env';

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
import {
  SimulationMode,
  type CreateEvalFormValues,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import { AppModelsEnumsAgentMode, TextRuntimeKind } from '@/client/types.gen';

import type { SimulationMode as SimulationModeType } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type {
  TextRuntimeKind as TextRuntimeKindType,
  VoiceSimulationConfigPublic,
} from '@/client/types.gen';

const SIMULATION_MODES = [
  { value: SimulationMode.TEXT, label: 'Text' },
  { value: SimulationMode.VOICE, label: 'Voice' },
] as const;

function voiceUnavailableReason(
  voiceSettings: VoiceSimulationConfigPublic | null | undefined
): ReactNode | undefined {
  if (!voiceSettings) {
    return (
      <>
        Voice simulations are not enabled on this deployment. Start Connexity with the voice
        Docker Compose overlay, or deploy voice on Kubernetes.
      </>
    );
  }
  if (!voiceSettings.voice_runtime_available) {
    return (
      <>
        Configure{' '}
        <span className="font-mono text-amber-600 dark:text-amber-400">TWILIO_ACCOUNT_SID</span>,{' '}
        <span className="font-mono text-amber-600 dark:text-amber-400">TWILIO_AUTH_TOKEN</span>, and{' '}
        <span className="font-mono text-amber-600 dark:text-amber-400">TWILIO_FROM_NUMBER</span> on
        the Connexity
        backend before saving or running voice eval configs.
      </>
    );
  }
  return undefined;
}

const disabledOptionTooltipClassName =
  'max-w-sm border-amber-400 bg-popover text-xs leading-relaxed text-popover-foreground shadow-md';

function DisabledOptionTooltip({
  reason,
  children,
}: {
  reason: ReactNode | undefined;
  children: ReactNode;
}) {
  if (!reason) {
    return <>{children}</>;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex">{children}</span>
      </TooltipTrigger>
      <TooltipContent side="bottom" className={disabledOptionTooltipClassName}>
        {reason}
      </TooltipContent>
    </Tooltip>
  );
}

function SimulationModeField({
  voiceSettings,
}: {
  voiceSettings: VoiceSimulationConfigPublic | null | undefined;
}) {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const voiceUnavailable =
    !voiceSettings || voiceSettings.voice_runtime_available === false;

  return (
    <FormField
      control={form.control}
      name="run.simulation_mode"
      render={({ field }) => (
        <FormItem className="col-span-2">
          <FieldLabel>Simulation mode</FieldLabel>
          <SimulationModeToggle
            value={field.value}
            readOnly={readOnly}
            voiceUnavailable={voiceUnavailable}
            voiceDisabledReason={voiceUnavailable ? voiceUnavailableReason(voiceSettings) : undefined}
            onChange={(mode) => {
              field.onChange(mode);
              if (mode === SimulationMode.VOICE) {
                form.setValue('run.tool_mode', 'mock', {
                  shouldDirty: true,
                  shouldValidate: true,
                });
                const currentDuration = form.getValues('run.max_call_duration_seconds');
                if (currentDuration == null || currentDuration < 1) {
                  form.setValue('run.max_call_duration_seconds', 300, {
                    shouldDirty: true,
                    shouldValidate: true,
                  });
                }
                const maxConcurrency = voiceSettings?.max_concurrency ?? 1;
                form.setValue('run.concurrency', Math.min(form.getValues('run.concurrency'), maxConcurrency), {
                  shouldDirty: true,
                  shouldValidate: true,
                });
                if (voiceSettings?.deployment_mode === 'local') {
                  form.setValue('run.concurrency', 1, {
                    shouldDirty: true,
                    shouldValidate: true,
                  });
                }
              }
            }}
          />
          <FieldHint>
            Text runs multi-turn chat simulations. Voice places a Twilio call to your agent and
            evaluates from the agent-side transcript after the call ends.
          </FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

interface SimulationModeToggleButtonProps {
  option: (typeof SIMULATION_MODES)[number];
  selected: boolean;
  voiceDisabled: boolean;
  voiceUnavailable: boolean;
  voiceDisabledReason: ReactNode | undefined;
  onSelect: (mode: SimulationModeType) => void;
}

function SimulationModeToggleButton({
  option,
  selected,
  voiceDisabled,
  voiceUnavailable,
  voiceDisabledReason,
  onSelect,
}: SimulationModeToggleButtonProps) {
  const isVoice = option.value === SimulationMode.VOICE;
  const baseClassName = 'px-4 py-1.5 rounded-md text-xs transition-all';

  const buildClassName = () => {
    if (selected && isVoice && voiceUnavailable) {
      return cn(
        baseClassName,
        'bg-amber-500/20 text-amber-400 border border-amber-500/30 shadow-sm',
        voiceDisabled && 'cursor-not-allowed opacity-60'
      );
    }

    if (selected) {
      return cn(
        baseClassName,
        'bg-accent text-foreground border border-border shadow-sm',
        voiceDisabled && 'cursor-not-allowed opacity-60'
      );
    }

    return cn(
      baseClassName,
      'text-muted-foreground hover:text-foreground',
      voiceDisabled && 'cursor-not-allowed opacity-60'
    );
  };

  const button = (
    <button
      type="button"
      disabled={voiceDisabled}
      onClick={() => onSelect(option.value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer',
        buildClassName()
      )}
    >
      {isVoice && voiceUnavailable ? (
        <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-amber-400 align-middle" />
      ) : null}
      {option.label}
    </button>
  );

  if (isVoice && voiceDisabled && voiceDisabledReason) {
    return <DisabledOptionTooltip reason={voiceDisabledReason}>{button}</DisabledOptionTooltip>;
  }

  return button;
}

function SimulationModeToggle({
  value,
  readOnly,
  voiceUnavailable,
  voiceDisabledReason,
  onChange,
}: {
  value: SimulationModeType;
  readOnly: boolean;
  voiceUnavailable: boolean;
  voiceDisabledReason: ReactNode | undefined;
  onChange: (mode: SimulationModeType) => void;
}) {
  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex w-fit items-center gap-1 rounded-lg border border-border bg-accent/20 p-0.5">
        {SIMULATION_MODES.map((option) => {
          const selected = value === option.value;
          const isVoice = option.value === SimulationMode.VOICE;
          const voiceDisabled = readOnly || (isVoice && voiceUnavailable);
          return (
            <SimulationModeToggleButton
              key={option.value}
              option={option}
              selected={selected}
              voiceDisabled={voiceDisabled}
              voiceUnavailable={voiceUnavailable}
              voiceDisabledReason={voiceDisabledReason}
              onSelect={onChange}
            />
          );
        })}
      </div>
    </TooltipProvider>
  );
}

function AgentPhoneNumberField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();

  return (
    <FormField
      control={form.control}
      name="run.agent_phone_number"
      render={({ field }) => (
        <FormItem className="col-span-2">
          <FieldLabel>Agent phone number</FieldLabel>
          <FormControl>
            <Input
              type="tel"
              className="h-9 text-sm"
              disabled={readOnly}
              placeholder="+1 555 123 4567"
              {...field}
            />
          </FormControl>
          <FieldHint>
            E.164 format (e.g. +15551234567). Connexity calls this number during voice evaluations;
            your agent should return a recording URL and transcript when the call ends.
          </FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function ConcurrencyField({
  isVoice,
  voiceSettings,
}: {
  isVoice: boolean;
  voiceSettings: VoiceSimulationConfigPublic | null | undefined;
}) {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const maxConcurrency = isVoice ? (voiceSettings?.max_concurrency ?? 1) : 50;
  const isLocalVoice = isVoice && voiceSettings?.deployment_mode === 'local';
  const fieldDisabled = readOnly || isLocalVoice;

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
              max={maxConcurrency}
              className="h-9 text-sm"
              disabled={fieldDisabled}
              value={isLocalVoice ? 1 : (field.value ?? '')}
              onChange={(e) => field.onChange(e.target.valueAsNumber)}
            />
          </FormControl>
          <FieldHint>
            {isLocalVoice
              ? 'Local voice deployments run one call at a time'
              : isVoice
                ? `Parallel voice calls (max ${maxConcurrency} on this deployment)`
                : 'Parallel scenarios at once'}
          </FieldHint>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function VoiceResultSubmissionPanel({
  voiceSettings,
}: {
  voiceSettings: VoiceSimulationConfigPublic;
}) {
  const { API_URL } = getPublicEnv();
  const submissionUrl = `${API_URL}${voiceSettings.result_submission_path}`;
  const loginUrl = `${API_URL}/api/v1/login/access-token`;

  return (
    <div className="col-span-2 space-y-2 rounded-lg border border-border/60 bg-accent/10 px-3 py-3">
      <p className="text-xs font-medium text-foreground">After each call ends</p>
      <p className="text-[11px] leading-relaxed text-muted-foreground">
        Your agent integration must POST the call recording URL and OpenAI-format conversation
        messages (including tool calls and tool results) to Connexity. The recording must include
        in-band DTMF tones Connexity sent during the call.
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-[11px]">
        <dt className="text-muted-foreground">Endpoint</dt>
        <dd className="break-all font-mono text-foreground">{submissionUrl}</dd>
        <dt className="text-muted-foreground">Auth</dt>
        <dd className="text-foreground">
          <span className="font-mono">Authorization: Bearer &lt;token&gt;</span> — obtain a JWT via{' '}
          <span className="font-mono">POST {loginUrl}</span> (same credentials as the Connexity UI)
          or reuse your browser session cookie when calling from a trusted server.
        </dd>
        <dt className="text-muted-foreground">Body</dt>
        <dd className="font-mono text-foreground">{`{ "audio_url": "...", "messages": [...] }`}</dd>
      </dl>
    </div>
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

function MaxCallDurationField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();

  return (
    <FormField
      control={form.control}
      name="run.max_call_duration_seconds"
      render={({ field }) => (
        <FormItem>
          <FieldLabel>Max call duration</FieldLabel>
          <FormControl>
            <Input
              type="number"
              min={1}
              max={3600}
              className="h-9 text-sm"
              disabled={readOnly}
              value={field.value ?? ''}
              onChange={(e) => field.onChange(e.target.valueAsNumber)}
            />
          </FormControl>
          <FieldHint>
            Maximum phone call length in seconds. Must be shorter than the per-test-case timeout
            (default 10 minutes).
          </FieldHint>
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
  liveDisabledReason: string | undefined;
  onSelect: (mode: ToolMode) => void;
}

function ToolModeToggleButton({
  mode,
  selected,
  liveDisabled,
  liveUnavailable,
  liveDisabledReason,
  onSelect,
}: ToolModeToggleButtonProps) {
  const baseClassName = 'px-4 py-1.5 rounded-md text-xs transition-all capitalize';

  const buildClassName = () => {
    if (selected && mode === 'live' && liveUnavailable) {
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

  const button = (
    <button
      type="button"
      disabled={liveDisabled}
      onClick={() => onSelect(mode)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer',
        buildClassName()
      )}
    >
      {mode === 'live' && liveUnavailable ? (
        <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-amber-400 align-middle" />
      ) : null}
      {mode.charAt(0).toUpperCase() + mode.slice(1)}
    </button>
  );

  if (mode === 'live' && liveDisabled && liveDisabledReason) {
    return <DisabledOptionTooltip reason={liveDisabledReason}>{button}</DisabledOptionTooltip>;
  }

  return button;
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

  const liveDisabledReason = liveUnavailable
    ? `Live tool calls unavailable: add HTTP endpoint (or Python) under each platform tool (${missingImpl.join(', ')}) — or leave Mock selected.`
    : undefined;

  return (
    <FormField
      control={form.control}
      name="run.tool_mode"
      render={({ field }) => (
        <FormItem className="col-span-2">
          <FieldLabel>Tool Calls</FieldLabel>

          <TooltipProvider delayDuration={200}>
            <div className="flex w-fit items-center gap-1 rounded-lg border border-border bg-accent/20 p-0.5">
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
                    liveDisabledReason={liveDisabledReason}
                    onSelect={field.onChange}
                  />
                );
              })}
            </div>
          </TooltipProvider>
          <FieldHint>
            Mock simulates tool responses from test case data. Live invokes stored HTTP or Python
            implementations for each platform tool during the run.
          </FieldHint>
          <FormMessage />
        </FormItem>
      )}
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
          <FieldLabel>Text runtime</FieldLabel>

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

interface RuntimeSectionProps {
  agentId: string;
  defaultToBackendOption?: boolean;
}

export function RuntimeSection({
  agentId,
  defaultToBackendOption = true,
}: RuntimeSectionProps) {
  const form = useFormContext<CreateEvalFormValues>();
  const simulationMode = form.watch('run.simulation_mode');
  const runtimeKind = form.watch('run.runtime.kind');
  const isVoice = simulationMode === SimulationMode.VOICE;
  const { data: agent } = useQuery({
    ...agentDetailQuery(agentId),
    enabled: !isVoice,
    staleTime: 30_000,
  });
  const { data: appConfig } = useQuery(appConfigQueries.root);
  const voiceSettings = appConfig?.voice_simulation ?? null;

  return (
    <Section>
      <Section.Header title="Simulation runtime" />
      <Section.Body>
        <div className="grid grid-cols-2 gap-4">
          <SimulationModeField voiceSettings={voiceSettings} />
          {isVoice ? (
            <AgentPhoneNumberField />
          ) : (
            <>
              <RuntimeField
                agentId={agentId}
                defaultToBackendOption={defaultToBackendOption}
              />
              <RunConfigToolModeSection
                agentMode={agent?.mode ?? null}
                agentTools={agent?.tools ?? null}
                runtimeKind={runtimeKind}
              />
            </>
          )}
          <ConcurrencyField isVoice={isVoice} voiceSettings={voiceSettings} />
          {isVoice ? <MaxCallDurationField /> : <MaxTurnsField />}
          {isVoice && voiceSettings ? (
            <VoiceResultSubmissionPanel voiceSettings={voiceSettings} />
          ) : null}
        </div>
      </Section.Body>
    </Section>
  );
}
