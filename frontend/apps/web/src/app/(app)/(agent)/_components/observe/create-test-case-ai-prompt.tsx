'use client';
'use no memo';

import { MessageSquare, Send, Sparkles, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import { cn } from '@workspace/ui/lib/utils';

import {
  STAGES,
  useCreateTestCaseAiPrompt,
} from '@/app/(app)/(agent)/_hooks/use-create-test-case-ai-prompt';

import type { CallPublic } from '@/client/types.gen';

interface CreateTestCaseAiPromptProps {
  agentId: string;
  call: CallPublic;
  onClose: () => void;
  onGenerated: (testCaseId: string) => void;
}

export function CreateTestCaseAiPrompt({
  agentId,
  call,
  onClose,
  onGenerated,
}: CreateTestCaseAiPromptProps) {
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
  } = useCreateTestCaseAiPrompt({ agentId, call, onClose, onGenerated });

  return (
    <div className="flex h-full w-[420px] shrink-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
        <div className="flex items-start justify-between gap-3 pr-2">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/15">
              <Sparkles className="h-4 w-4 text-violet-400" />
            </div>
            <div>
              <p className="text-sm text-foreground">Generate with AI</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                Describe the scenario to cover
              </p>
            </div>
          </div>
          {phase === 'input' ? (
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {phase === 'input' ? (
          <>
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-violet-500/20 bg-violet-500/5 px-3 py-2.5">
              <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />

              <p className="text-[11px] leading-snug text-violet-300/80">
                AI will read this <span className="text-violet-300">conversation</span> and your{' '}
                <span className="text-violet-300">agent prompt</span> to create a relevant test
                case(s)
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
                Call ID: <span className="font-mono">{call.id.slice(0, 8)}</span>
              </p>

              {error ? (
                <p className="mt-2 text-xs text-destructive" role="alert">
                  {error}
                </p>
              ) : null}
            </div>
          </>
        ) : (
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
                const status = i < stageIndex ? 'done' : i === stageIndex ? 'active' : 'pending';
                return (
                  <div
                    key={stage.label}
                    className={cn(
                      'flex items-center gap-2 text-[11px] transition-colors',
                      status === 'done' && 'text-muted-foreground',
                      status === 'active' && 'text-foreground',
                      status === 'pending' && 'text-muted-foreground/30'
                    )}
                  >
                    <span
                      className={cn(
                        'h-1.5 w-1.5 shrink-0 rounded-full',
                        status === 'done' && 'bg-violet-400',
                        status === 'active' && 'animate-pulse bg-violet-400',
                        status === 'pending' && 'bg-muted-foreground/20'
                      )}
                    />
                    {stage.label}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {phase === 'input' ? (
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
            className="h-8 gap-1.5 border-0 bg-violet-600 text-xs text-white hover:bg-violet-500"
            disabled={!userPrompt.trim() || isPending}
            onClick={() => void handleGenerate()}
          >
            <Send className="h-3.5 w-3.5" />
            Generate
          </Button>
        </div>
      ) : null}
    </div>
  );
}
