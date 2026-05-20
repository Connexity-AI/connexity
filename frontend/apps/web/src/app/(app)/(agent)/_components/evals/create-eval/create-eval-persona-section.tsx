'use client';
'use no memo';

import { useEffect } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Slider } from '@workspace/ui/components/ui/slider';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import {
  FieldLabel,
  Section,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-section-primitives';
import {
  SimulationMode,
  type CreateEvalFormValues,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import { SpeechModelPicker } from '@/app/(app)/(agent)/_components/speech/speech-model-picker';
import { TtsVoicePicker } from '@/app/(app)/(agent)/_components/speech/tts-voice-picker';
import { LlmModelPicker } from '@/app/(app)/(agent)/_components/llm/llm-model-picker';
import { useSttModels } from '@/app/(app)/(agent)/_hooks/use-stt-models';
import { useTtsModels } from '@/app/(app)/(agent)/_hooks/use-tts-models';
import { useTtsVoices } from '@/app/(app)/(agent)/_hooks/use-tts-voices';
import { temperatureLabel } from '@/app/(app)/(agent)/_constants/agent';
import {
  defaultVoiceIdFromCatalog,
  speechSelectionFromCatalog,
} from '@/utils/speech-defaults-from-catalog';

function LlmModelField() {
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

function SttModelField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const { data: catalog, isFetching } = useSttModels();
  const sttProvider = useWatch({ control: form.control, name: 'persona.stt.provider' });

  return (
    <FormField
      control={form.control}
      name="persona.stt.model"
      render={({ field }) => (
        <FormItem>
          <FieldLabel>STT Model</FieldLabel>
          <SpeechModelPicker
            catalog={catalog.data}
            isFetching={isFetching}
            value={field.value}
            provider={sttProvider}
            ariaLabel="STT model"
            placeholder="Select STT model"
            onSelect={(modelOption) => {
              form.setValue('persona.stt.provider', modelOption.provider, { shouldDirty: true });
              field.onChange(modelOption.model);
            }}
            disabled={readOnly}
          />
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function TtsModelField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const { data: catalog, isFetching } = useTtsModels();
  const ttsProvider = useWatch({ control: form.control, name: 'persona.tts.provider' });

  return (
    <FormField
      control={form.control}
      name="persona.tts.model"
      render={({ field }) => (
        <FormItem>
          <FieldLabel>TTS Model</FieldLabel>
          <SpeechModelPicker
            catalog={catalog.data}
            isFetching={isFetching}
            value={field.value}
            provider={ttsProvider}
            ariaLabel="TTS model"
            placeholder="Select TTS model"
            onSelect={(modelOption) => {
              form.setValue('persona.tts.provider', modelOption.provider, { shouldDirty: true });
              field.onChange(modelOption.model);
              form.setValue('persona.tts.voice_id', '', { shouldDirty: true });
            }}
            disabled={readOnly}
          />
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function TtsVoiceField() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const isVoice =
    useWatch({ control: form.control, name: 'run.simulation_mode' }) === SimulationMode.VOICE;
  const ttsProvider = useWatch({ control: form.control, name: 'persona.tts.provider' });
  const ttsModel = useWatch({ control: form.control, name: 'persona.tts.model' });
  const voiceId = useWatch({ control: form.control, name: 'persona.tts.voice_id' });
  const { data: voicesCatalog } = useTtsVoices(ttsProvider, ttsModel);

  useEffect(() => {
    if (!isVoice || readOnly || voiceId.trim() || !ttsProvider.trim() || !ttsModel.trim()) {
      return;
    }
    const defaultVoice = defaultVoiceIdFromCatalog(voicesCatalog);
    if (!defaultVoice) {
      return;
    }
    form.setValue('persona.tts.voice_id', defaultVoice, { shouldDirty: false });
  }, [
    form,
    isVoice,
    readOnly,
    voiceId,
    ttsProvider,
    ttsModel,
    voicesCatalog.count,
    voicesCatalog.default_voice_id,
    voicesCatalog.data,
  ]);

  return (
    <FormField
      control={form.control}
      name="persona.tts.voice_id"
      render={({ field }) => (
        <FormItem>
          <FieldLabel>TTS Voice</FieldLabel>
          <TtsVoicePicker
            provider={ttsProvider}
            model={ttsModel}
            value={field.value}
            disabled={readOnly}
            onSelect={(voiceId) => field.onChange(voiceId)}
          />
          <FormMessage />
        </FormItem>
      )}
    />
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

function LlmFields() {
  return (
    <div className="space-y-4">
      <LlmModelField />
      <TemperatureField />
    </div>
  );
}

export function PersonaSection() {
  const form = useFormContext<CreateEvalFormValues>();
  const readOnly = useCreateEvalReadOnly();
  const simulationMode = useWatch({ control: form.control, name: 'run.simulation_mode' });
  const isVoice = simulationMode === SimulationMode.VOICE;
  const { data: sttCatalog } = useSttModels();
  const { data: ttsCatalog } = useTtsModels();

  useEffect(() => {
    if (!isVoice || readOnly) {
      return;
    }
    const stt = form.getValues('persona.stt');
    if (!stt.provider.trim() || !stt.model.trim()) {
      const selection = speechSelectionFromCatalog(sttCatalog);
      if (selection.provider && selection.model) {
        form.setValue('persona.stt', selection, { shouldDirty: false });
      }
    }
    const tts = form.getValues('persona.tts');
    if (!tts.provider.trim() || !tts.model.trim()) {
      const selection = speechSelectionFromCatalog(ttsCatalog);
      if (selection.provider && selection.model) {
        form.setValue(
          'persona.tts',
          { ...selection, voice_id: tts.voice_id },
          { shouldDirty: false }
        );
      }
    }
  }, [form, isVoice, readOnly, sttCatalog, ttsCatalog]);

  return (
    <Section>
      <Section.Header title="Persona Simulation" />
      <Section.Body>
        <div className="space-y-4">
          {isVoice ? <SttModelField /> : null}
          <LlmFields />
          {isVoice ? (
            <>
              <TtsModelField />
              <TtsVoiceField />
            </>
          ) : null}
        </div>
      </Section.Body>
    </Section>
  );
}
