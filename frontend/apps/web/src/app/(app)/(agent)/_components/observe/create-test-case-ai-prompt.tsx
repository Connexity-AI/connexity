'use client';
'use no memo';

import type { RefObject } from 'react';

import { ChevronLeft, ChevronRight, MessageSquare, Send, Sparkles, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import { cn } from '@workspace/ui/lib/utils';

import { AddTestCaseAiResultsPhase } from '@/app/(app)/(agent)/_components/evals/test-cases/add-test-case-ai-results-phase';
import {
  STAGES,
  useCreateTestCaseAiPrompt,
  type AiPromptPhase,
} from '@/app/(app)/(agent)/_hooks/use-create-test-case-ai-prompt';

import type { CarouselApi } from '@workspace/ui/components/ui/carousel';
import type { CallPublic, TestCasePublic } from '@/client/types.gen';

type StageStatus = 'done' | 'active' | 'pending';

const HEADER_TEXT: Record<AiPromptPhase, { title: string; subtitle: string }> = {
  input: { title: 'Generate with AI', subtitle: 'Describe the scenario to cover' },
  generating: { title: 'Generate with AI', subtitle: 'Describe the scenario to cover' },
  results: { title: 'Generated test cases', subtitle: 'Review and edit what AI created' },
};

const STAGE_ROW_CLASSES: Record<StageStatus, string> = {
  done: 'text-muted-foreground',
  active: 'text-foreground',
  pending: 'text-muted-foreground/30',
};

const STAGE_DOT_CLASSES: Record<StageStatus, string> = {
  done: 'bg-violet-400',
  active: 'animate-pulse bg-violet-400',
  pending: 'bg-muted-foreground/20',
};

function getStageStatus(index: number, currentStage: number): StageStatus {
  if (index < currentStage) return 'done';
  if (index === currentStage) return 'active';
  return 'pending';
}

interface CreateTestCaseAiPromptProps {
  agentId: string;
  call: CallPublic;
  onClose: () => void;
}

export function CreateTestCaseAiPrompt({ agentId, call, onClose }: CreateTestCaseAiPromptProps) {
  const {
    phase,
    userPrompt,
    setUserPrompt,
    stageIndex,
    progress,
    error,
    textareaRef,
    isPending,
    handleGenerate,
    handleKeyDown,
    generatedTestCases,
    setCarouselApi,
    currentIndex,
    canScrollPrev,
    canScrollNext,
    scrollPrev,
    scrollNext,
  } = useCreateTestCaseAiPrompt({ agentId, call, onClose });

  return (
    <div className="flex h-full w-[420px] shrink-0 flex-col overflow-hidden">
      <Header
        phase={phase}
        carouselCount={generatedTestCases.length}
        currentIndex={currentIndex}
        canScrollPrev={canScrollPrev}
        canScrollNext={canScrollNext}
        scrollPrev={scrollPrev}
        scrollNext={scrollNext}
        onClose={onClose}
      />

      <Body
        phase={phase}
        agentId={agentId}
        call={call}
        userPrompt={userPrompt}
        setUserPrompt={setUserPrompt}
        textareaRef={textareaRef}
        handleKeyDown={handleKeyDown}
        error={error}
        stageIndex={stageIndex}
        progress={progress}
        generatedTestCases={generatedTestCases}
        setCarouselApi={setCarouselApi}
      />

      <Footer
        phase={phase}
        userPrompt={userPrompt}
        isPending={isPending}
        handleGenerate={handleGenerate}
        onClose={onClose}
      />
    </div>
  );
}

interface HeaderProps {
  phase: AiPromptPhase;
  carouselCount: number;
  currentIndex: number;
  canScrollPrev: boolean;
  canScrollNext: boolean;
  scrollPrev: () => void;
  scrollNext: () => void;
  onClose: () => void;
}

function Header({
  phase,
  carouselCount,
  currentIndex,
  canScrollPrev,
  canScrollNext,
  scrollPrev,
  scrollNext,
  onClose,
}: HeaderProps) {
  const { title, subtitle } = HEADER_TEXT[phase];

  return (
    <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
      <div className="flex items-start justify-between gap-3 pr-2">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/15">
            <Sparkles className="h-4 w-4 text-violet-400" />
          </div>
          <div>
            <p className="text-sm text-foreground">{title}</p>
            <p className="mt-0.5 text-[11px] text-muted-foreground">{subtitle}</p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <CarouselNav
            phase={phase}
            count={carouselCount}
            currentIndex={currentIndex}
            canScrollPrev={canScrollPrev}
            canScrollNext={canScrollNext}
            scrollPrev={scrollPrev}
            scrollNext={scrollNext}
          />
          <CloseButton phase={phase} onClose={onClose} />
        </div>
      </div>
    </div>
  );
}

interface CarouselNavProps {
  phase: AiPromptPhase;
  count: number;
  currentIndex: number;
  canScrollPrev: boolean;
  canScrollNext: boolean;
  scrollPrev: () => void;
  scrollNext: () => void;
}

function CarouselNav({
  phase,
  count,
  currentIndex,
  canScrollPrev,
  canScrollNext,
  scrollPrev,
  scrollNext,
}: CarouselNavProps) {
  if (phase !== 'results') return null;
  if (count <= 1) return null;

  return (
    <div className="flex items-center gap-0.5 rounded-md border border-border bg-accent/40 px-1 py-0.5">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={scrollPrev}
        disabled={!canScrollPrev}
        aria-label="Previous test case"
        className="h-5 w-5 rounded text-muted-foreground hover:bg-transparent hover:text-foreground disabled:opacity-30 [&_svg]:size-3.5"
      >
        <ChevronLeft />
      </Button>
      <span className="min-w-[34px] px-1 text-center text-[11px] tabular-nums text-foreground">
        {currentIndex + 1} / {count}
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={scrollNext}
        disabled={!canScrollNext}
        aria-label="Next test case"
        className="h-5 w-5 rounded text-muted-foreground hover:bg-transparent hover:text-foreground disabled:opacity-30 [&_svg]:size-3.5"
      >
        <ChevronRight />
      </Button>
    </div>
  );
}

interface CloseButtonProps {
  phase: AiPromptPhase;
  onClose: () => void;
}

function CloseButton({ phase, onClose }: CloseButtonProps) {
  if (phase === 'generating') return null;

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={onClose}
      aria-label="Close"
      className="h-7 w-7 rounded p-1 text-muted-foreground hover:bg-transparent hover:text-foreground"
    >
      <X />
    </Button>
  );
}

interface BodyProps {
  phase: AiPromptPhase;
  agentId: string;
  call: CallPublic;
  userPrompt: string;
  setUserPrompt: (value: string) => void;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  error: string | null;
  stageIndex: number;
  progress: number;
  generatedTestCases: TestCasePublic[];
  setCarouselApi: (api: CarouselApi | undefined) => void;
}

function Body(props: BodyProps) {
  if (props.phase === 'input') {
    return (
      <InputBody
        userPrompt={props.userPrompt}
        setUserPrompt={props.setUserPrompt}
        textareaRef={props.textareaRef}
        handleKeyDown={props.handleKeyDown}
        error={props.error}
        callId={props.call.id}
      />
    );
  }
  if (props.phase === 'generating') {
    return <GeneratingBody stageIndex={props.stageIndex} progress={props.progress} />;
  }
  return (
    <ResultsBody
      agentId={props.agentId}
      generatedTestCases={props.generatedTestCases}
      setCarouselApi={props.setCarouselApi}
    />
  );
}

interface InputBodyProps {
  userPrompt: string;
  setUserPrompt: (value: string) => void;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  error: string | null;
  callId: string;
}

function InputBody({
  userPrompt,
  setUserPrompt,
  textareaRef,
  handleKeyDown,
  error,
  callId,
}: InputBodyProps) {
  return (
    <div className="flex-1 overflow-y-auto px-5 py-4">
      <div className="mb-4 flex items-start gap-2 rounded-lg border border-violet-500/20 bg-violet-500/5 px-3 py-2.5">
        <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />
        <p className="text-[11px] leading-snug text-violet-300/80">
          AI will read this <span className="text-violet-300">conversation</span> and your{' '}
          <span className="text-violet-300">agent prompt</span> to create a relevant test case(s)
        </p>
      </div>

      <div>
        <label className="mb-1.5 block text-xs text-muted-foreground">
          What should this test case(s) cover?
        </label>

        <Textarea
          ref={textareaRef}
          value={userPrompt}
          onChange={(e) => setUserPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Generate a test case covering the out-of-scope request from this call, ensuring polite decline and redirection…"
          className="h-48 resize-none text-sm"
        />

        <p className="mt-1.5 text-[10px] text-muted-foreground/40">
          Call ID: <span className="font-mono">{callId.slice(0, 8)}</span>
        </p>

        <ErrorMessage error={error} />
      </div>
    </div>
  );
}

function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <p className="mt-2 text-xs text-destructive" role="alert">
      {error}
    </p>
  );
}

interface GeneratingBodyProps {
  stageIndex: number;
  progress: number;
}

function GeneratingBody({ stageIndex, progress }: GeneratingBodyProps) {
  return (
    <div className="flex-1 overflow-y-auto px-5 py-4">
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{STAGES[stageIndex]?.label}</span>
            <span className="text-xs tabular-nums text-muted-foreground/50">{progress}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-accent">
            <div
              className="h-full rounded-full bg-violet-500 transition-all duration-100"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <div className="space-y-1.5">
          {STAGES.map((stage, i) => {
            const status = getStageStatus(i, stageIndex);
            return (
              <div
                key={stage.label}
                className={cn(
                  'flex items-center gap-2 text-[11px] transition-colors',
                  STAGE_ROW_CLASSES[status],
                )}
              >
                <span
                  className={cn('h-1.5 w-1.5 shrink-0 rounded-full', STAGE_DOT_CLASSES[status])}
                />
                {stage.label}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

interface ResultsBodyProps {
  agentId: string;
  generatedTestCases: TestCasePublic[];
  setCarouselApi: (api: CarouselApi | undefined) => void;
}

function ResultsBody({ agentId, generatedTestCases, setCarouselApi }: ResultsBodyProps) {
  return (
    <div className="flex-1 overflow-y-auto px-5 py-4">
      <AddTestCaseAiResultsPhase
        agentId={agentId}
        testCases={generatedTestCases}
        setApi={setCarouselApi}
      />
    </div>
  );
}

interface FooterProps {
  phase: AiPromptPhase;
  userPrompt: string;
  isPending: boolean;
  handleGenerate: () => Promise<void>;
  onClose: () => void;
}

function Footer({ phase, userPrompt, isPending, handleGenerate, onClose }: FooterProps) {
  if (phase === 'input') {
    return (
      <InputFooter
        userPrompt={userPrompt}
        isPending={isPending}
        handleGenerate={handleGenerate}
        onClose={onClose}
      />
    );
  }
  if (phase === 'results') {
    return <ResultsFooter onClose={onClose} />;
  }
  return null;
}

interface InputFooterProps {
  userPrompt: string;
  isPending: boolean;
  handleGenerate: () => Promise<void>;
  onClose: () => void;
}

function InputFooter({ userPrompt, isPending, handleGenerate, onClose }: InputFooterProps) {
  return (
    <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border px-5 py-4">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-8 text-xs"
        onClick={onClose}
        disabled={isPending}
      >
        Cancel
      </Button>

      <Button
        type="button"
        size="sm"
        className="h-8 gap-1.5 border-0 bg-violet-600 text-xs text-white hover:bg-violet-500 [&_svg]:size-3.5"
        disabled={!userPrompt.trim() || isPending}
        onClick={() => void handleGenerate()}
      >
        <Send />
        Generate
      </Button>
    </div>
  );
}

function ResultsFooter({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border px-5 py-4">
      <Button
        type="button"
        size="sm"
        className="h-8 border-0 bg-violet-600 text-xs text-white hover:bg-violet-500"
        onClick={onClose}
      >
        Done
      </Button>
    </div>
  );
}
