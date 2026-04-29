'use client';

import { useEffect, useRef, useState } from 'react';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useEditTestCaseAiAgent } from '@/app/(app)/(agent)/_hooks/use-edit-test-case-ai-agent';
import { isErrorApiResult } from '@/utils/api';

import type { TestCasePublic } from '@/client/types.gen';

export const AI_EDIT_STAGES = [
  { label: 'Reading current test case…', duration: 2250 },
  { label: 'Understanding requested changes…', duration: 3000 },
  { label: 'Applying edits…', duration: 3750 },
  { label: 'Finalising…', duration: 1500 },
];

export const aiEditSchema = z.object({
  prompt: z.string().min(1, 'Describe what should change'),
});

export type AiEditValues = z.infer<typeof aiEditSchema>;

export type AiEditPhase = 'input' | 'generating';

const TICK_MS = 30;
const COMPLETION_DELAY_MS = 200;
const HOLD_PROGRESS_AT = 95;

interface UseTestCaseAiEditOptions {
  agentId: string;
  testCaseId: string;
  onApply: (edited: TestCasePublic) => void;
}

export function useTestCaseAiEdit({ agentId, testCaseId, onApply }: UseTestCaseAiEditOptions) {
  const [phase, setPhase] = useState<AiEditPhase>('input');
  const [stageIndex, setStageIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const frameRef = useRef<number | null>(null);

  const { mutateAsync, isPending, error, reset } = useEditTestCaseAiAgent(agentId);

  const form = useForm<AiEditValues>({
    resolver: zodResolver(aiEditSchema),
    defaultValues: { prompt: '' },
  });

  useEffect(() => {
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, []);

  const cancelAnimation = () => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
  };

  const startStageAnimation = () => {
    setPhase('generating');
    setStageIndex(0);
    setProgress(0);

    let elapsed = 0;
    const total = AI_EDIT_STAGES.reduce((sum, stage) => sum + stage.duration, 0);
    const lastStageIndex = AI_EDIT_STAGES.length - 1;

    const runStage = (idx: number) => {
      const stage = AI_EDIT_STAGES[idx];
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

  const runEdit = async (values: AiEditValues) => {
    reset();
    startStageAnimation();

    const result = await mutateAsync({ testCaseId, prompt: values.prompt });

    cancelAnimation();

    if (isErrorApiResult(result)) {
      setPhase('input');
      setStageIndex(0);
      setProgress(0);
      return;
    }

    setProgress(100);

    const edited = result.data?.edited;
    if (!edited) {
      setPhase('input');
      return;
    }

    setTimeout(() => onApply(edited), COMPLETION_DELAY_MS);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    void form.handleSubmit(runEdit)(event);
  };

  const submit = () => {
    void form.handleSubmit(runEdit)();
  };

  return {
    form,
    phase,
    stageIndex,
    progress,
    error,
    isPending,
    handleSubmit,
    submit,
  };
}
