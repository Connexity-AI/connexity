'use client';
'use no memo';

import { useMemo } from 'react';

import { Loader2 } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import { Carousel, CarouselContent, CarouselItem } from '@workspace/ui/components/ui/carousel';
import { Form } from '@workspace/ui/components/ui/form';

import { TestCaseBasicInfoSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-basic-info-section';
import { TestCaseEvaluationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-evaluation-section';
import { TestCaseUserSimulationSection } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-user-simulation-section';
import { useTestCaseDetailForm } from '@/app/(app)/(agent)/_hooks/use-test-case-detail-form';

import type { CarouselApi } from '@workspace/ui/components/ui/carousel';
import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import type { TestCasePublic } from '@/client/types.gen';

interface AddTestCaseAiResultsPhaseProps {
  agentId: string;
  testCases: TestCasePublic[];
  setApi: (api: CarouselApi | undefined) => void;
}

export function AddTestCaseAiResultsPhase({
  agentId,
  testCases,
  setApi,
}: AddTestCaseAiResultsPhaseProps) {
  return (
    <Carousel
      setApi={setApi}
      opts={{ align: 'start', containScroll: 'trimSnaps' }}
      className="w-full"
    >
      <CarouselContent className="ml-0">
        {testCases.map((tc) => (
          <CarouselItem key={tc.id} className="pl-0">
            <EditableSlide agentId={agentId} testCase={tc} />
          </CarouselItem>
        ))}
      </CarouselContent>
    </Carousel>
  );
}

function EditableSlide({ agentId, testCase }: { agentId: string; testCase: TestCasePublic }) {
  const agentForm = useFormContext<AgentFormValues>();
  const watchedTools = agentForm?.watch('tools');
  const availableTools = useMemo(() => watchedTools ?? [], [watchedTools]);

  const { form, handleSubmit, isPending } = useTestCaseDetailForm({
    agentId,
    testCase,
    availableTools,
    onSuccess: () => {},
  });

  return (
    <Form {...form}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <TestCaseBasicInfoSection />
        <TestCaseUserSimulationSection />
        <TestCaseEvaluationSection availableTools={availableTools} />

        <div className="flex justify-end">
          <Button type="submit" size="sm" className="h-7 gap-1.5 text-xs" disabled={isPending}>
            {isPending && <Loader2 className="h-3 w-3 animate-spin" />}
            Save changes
          </Button>
        </div>
      </form>
    </Form>
  );
}
