'use client';
'use no memo';

import { createContext, useContext, type ReactNode } from 'react';

import { Button } from '@workspace/ui/components/ui/button';
import { Form } from '@workspace/ui/components/ui/form';
import { Sheet, SheetContent } from '@workspace/ui/components/ui/sheet';

import { AddTestCaseAiDrawerFooter } from './add-test-case-ai-drawer-footer';
import { AddTestCaseAiDrawerHeader } from './add-test-case-ai-drawer-header';
import { AddTestCaseAiGeneratingPhase } from './add-test-case-ai-generating-phase';
import { AddTestCaseAiInputPhase } from './add-test-case-ai-input-phase';
import { AddTestCaseAiResultsPhase } from './add-test-case-ai-results-phase';
import {
  useAiTestCaseGeneration,
  type UseAiTestCaseGenerationReturn,
} from './use-ai-test-case-generation';

type AiDrawerContextValue = UseAiTestCaseGenerationReturn;

const AiDrawerContext = createContext<AiDrawerContextValue | null>(null);

function useAiDrawerContext() {
  const ctx = useContext(AiDrawerContext);
  if (!ctx) {
    throw new Error('AiTestCaseDrawer parts must be rendered inside <AiTestCaseDrawer.Root>');
  }
  return ctx;
}

interface RootProps {
  agentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

function Root({ agentId, open, onOpenChange, children }: RootProps) {
  const generation = useAiTestCaseGeneration({ agentId, onOpenChange });

  return (
    <AiDrawerContext.Provider value={generation}>
      <Sheet open={open} onOpenChange={generation.onOpenChange}>
        {children}
      </Sheet>
    </AiDrawerContext.Provider>
  );
}

function Content({ children }: { children: ReactNode }) {
  const { form, handleSubmit } = useAiDrawerContext();
  return (
    <SheetContent
      side="right"
      className="flex h-full w-full flex-col gap-0 overflow-hidden border-l border-border p-0 sm:max-w-105"
    >
      <Form {...form}>
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          {children}
        </form>
      </Form>
    </SheetContent>
  );
}

function Body({ children }: { children: ReactNode }) {
  return <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>;
}

function Header() {
  const {
    phase,
    generatedTestCases,
    currentIndex,
    canScrollPrev,
    canScrollNext,
    scrollPrev,
    scrollNext,
  } = useAiDrawerContext();

  if (phase === 'results') {
    return (
      <AddTestCaseAiDrawerHeader
        variant="results"
        carousel={{
          current: currentIndex,
          total: generatedTestCases.length,
          canScrollPrev,
          canScrollNext,
          onPrev: scrollPrev,
          onNext: scrollNext,
        }}
      />
    );
  }

  return <AddTestCaseAiDrawerHeader />;
}

function InputPhase() {
  const { phase, error } = useAiDrawerContext();
  if (phase !== 'input') return null;
  return <AddTestCaseAiInputPhase error={error} />;
}

function GeneratingPhase() {
  const { phase, stageIndex, progress } = useAiDrawerContext();
  if (phase !== 'generating') return null;
  return <AddTestCaseAiGeneratingPhase stageIndex={stageIndex} progress={progress} />;
}

function ResultsPhase() {
  const { phase, generatedTestCases, setCarouselApi } = useAiDrawerContext();
  if (phase !== 'results') return null;
  return <AddTestCaseAiResultsPhase testCases={generatedTestCases} setApi={setCarouselApi} />;
}

function Footer() {
  const { phase, onOpenChange } = useAiDrawerContext();

  if (phase === 'results') {
    return (
      <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border px-5 py-4">
        <Button
          type="button"
          size="sm"
          className="h-8 border-0 bg-violet-600 text-xs text-white hover:bg-violet-500"
          onClick={() => onOpenChange(false)}
        >
          Done
        </Button>
      </div>
    );
  }

  if (phase !== 'input') return null;
  return <AddTestCaseAiDrawerFooter onCancel={() => onOpenChange(false)} />;
}

export const AiTestCaseDrawer = {
  Root,
  Content,
  Header,
  Body,
  InputPhase,
  GeneratingPhase,
  ResultsPhase,
  Footer,
};

interface AddTestCaseAiDrawerProps {
  agentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddTestCaseAiDrawer({ agentId, open, onOpenChange }: AddTestCaseAiDrawerProps) {
  return (
    <AiTestCaseDrawer.Root agentId={agentId} open={open} onOpenChange={onOpenChange}>
      <AiTestCaseDrawer.Content>
        <AiTestCaseDrawer.Header />
        <AiTestCaseDrawer.Body>
          <AiTestCaseDrawer.InputPhase />
          <AiTestCaseDrawer.GeneratingPhase />
          <AiTestCaseDrawer.ResultsPhase />
        </AiTestCaseDrawer.Body>
        <AiTestCaseDrawer.Footer />
      </AiTestCaseDrawer.Content>
    </AiTestCaseDrawer.Root>
  );
}
