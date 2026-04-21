'use client';
'use no memo';

import { createContext, useContext, type ReactNode } from 'react';

import { Form } from '@workspace/ui/components/ui/form';
import { Sheet, SheetContent } from '@workspace/ui/components/ui/sheet';

import { AddTestCaseAiDrawerFooter } from './add-test-case-ai-drawer-footer';
import { AddTestCaseAiDrawerHeader } from './add-test-case-ai-drawer-header';
import { AddTestCaseAiGeneratingPhase } from './add-test-case-ai-generating-phase';
import { AddTestCaseAiInputPhase } from './add-test-case-ai-input-phase';
import { useAiTestCaseGeneration } from './use-ai-test-case-generation';

type AiDrawerContextValue = ReturnType<typeof useAiTestCaseGeneration>;

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

function Footer() {
  const { phase, onOpenChange } = useAiDrawerContext();
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
        </AiTestCaseDrawer.Body>
        <AiTestCaseDrawer.Footer />
      </AiTestCaseDrawer.Content>
    </AiTestCaseDrawer.Root>
  );
}
