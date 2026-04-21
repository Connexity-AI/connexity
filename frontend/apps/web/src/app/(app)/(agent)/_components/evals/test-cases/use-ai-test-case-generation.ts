'use client';

import { useRef, useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useRunTestCaseAiAgent } from '@/app/(app)/(agent)/_hooks/use-run-test-case-ai-agent';
import { isErrorApiResult } from '@/utils/api';

export const AI_GENERATION_STAGES = [
  { label: 'Reading agent prompt…', duration: 2625 },
  { label: 'Analysing existing test cases…', duration: 3375 },
  { label: 'Generating persona and scenario…', duration: 4125 },
  { label: 'Building expected outcomes…', duration: 3000 },
  { label: 'Finalising test case…', duration: 1875 },
];

export const addTestCaseAiSchema = z.object({
  prompt: z.string().min(1, 'Describe what this test case should cover'),
});

export type AddTestCaseAiValues = z.infer<typeof addTestCaseAiSchema>;

export type AiGenerationPhase = 'input' | 'generating';

const TICK_MS = 30;
const COMPLETION_DELAY_MS = 200;
const HOLD_PROGRESS_AT = 95;

interface UseAiTestCaseGenerationOptions {
  agentId: string;
  onOpenChange: (open: boolean) => void;
}

export function useAiTestCaseGeneration({
  agentId,
  onOpenChange,
}: UseAiTestCaseGenerationOptions) {
  const [phase, setPhase] = useState<AiGenerationPhase>('input');
  const [stageIndex, setStageIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const frameRef = useRef<number | null>(null);

  const { mutateAsync, isPending, error, reset } = useRunTestCaseAiAgent(agentId);

  const form = useForm<AddTestCaseAiValues>({
    resolver: zodResolver(addTestCaseAiSchema),
    defaultValues: { prompt: '' },
  });

  const cancelAnimation = () => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      cancelAnimation();
      setPhase('input');
      setStageIndex(0);
      setProgress(0);
      form.reset({ prompt: '' });
      reset();
    }
    onOpenChange(next);
  };

  const startStageAnimation = () => {
    setPhase('generating');
    setStageIndex(0);
    setProgress(0);

    let elapsed = 0;
    const total = AI_GENERATION_STAGES.reduce((sum, stage) => sum + stage.duration, 0);
    const lastStageIndex = AI_GENERATION_STAGES.length - 1;

    const runStage = (idx: number) => {
      const stage = AI_GENERATION_STAGES[idx];
      if (!stage) return;
      setStageIndex(idx);
      const end = elapsed + stage.duration;

      const tick = () => {
        elapsed += TICK_MS;
        const computed = Math.min(100, Math.round((elapsed / total) * 100));
        setProgress(idx === lastStageIndex ? Math.min(HOLD_PROGRESS_AT, computed) : computed);
        if (elapsed < end) {
          frameRef.current = requestAnimationFrame(tick);
        } else {
          elapsed = end;
          if (idx < lastStageIndex) {
            runStage(idx + 1);
          } else {
            setProgress(HOLD_PROGRESS_AT);
            frameRef.current = null;
          }
        }
      };
      frameRef.current = requestAnimationFrame(tick);
    };

    runStage(0);
  };

  const runGeneration = async (values: AddTestCaseAiValues) => {
    reset();
    startStageAnimation();

    const result = await mutateAsync({ prompt: values.prompt });

    cancelAnimation();

    if (isErrorApiResult(result)) {
      setPhase('input');
      setStageIndex(0);
      setProgress(0);
      return;
    }

    setProgress(100);
    setTimeout(() => handleOpenChange(false), COMPLETION_DELAY_MS);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    void form.handleSubmit(runGeneration)(event);
  };

  return {
    form,
    phase,
    stageIndex,
    progress,
    error,
    isPending,
    handleSubmit,
    onOpenChange: handleOpenChange,
  };
}
