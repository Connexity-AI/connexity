'use client';
'use no memo';

import { Brain, Send, Sparkles, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Form, FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import { cn } from '@workspace/ui/lib/utils';

import {
  AI_EDIT_STAGES,
  useTestCaseAiEdit,
} from '@/app/(app)/(agent)/_components/evals/test-cases/use-test-case-ai-edit';

import type { TestCasePublic } from '@/client/types.gen';

interface Props {
  agentId: string;
  testCaseId: string;
  onApply: (edited: TestCasePublic) => void;
  onClose: () => void;
}

export function TestCaseAiEditPanel({ agentId, testCaseId, onApply, onClose }: Props) {
  const { form, phase, stageIndex, progress, error, isPending, handleSubmit, submit } =
    useTestCaseAiEdit({ agentId, testCaseId, onApply });

  return (
    <div className="absolute inset-0 z-10 flex flex-col bg-background">
      <Form {...form}>
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/15">
                  <Sparkles className="h-4 w-4 text-violet-400" />
                </div>
                <div>
                  <p className="text-sm text-foreground">AI Assistant</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Describe what to change
                  </p>
                </div>
              </div>
              {phase === 'input' && (
                <button
                  type="button"
                  onClick={onClose}
                  className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            {phase === 'input' && (
              <>
                <div className="mb-4 flex items-start gap-2 rounded-lg border border-violet-500/20 bg-violet-500/5 px-3 py-2.5">
                  <Brain className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />
                  <p className="text-[11px] leading-snug text-violet-300/80">
                    AI will update only{' '}
                    <span className="text-violet-300">this test case</span> based on your request
                  </p>
                </div>

                <FormField
                  control={form.control}
                  name="prompt"
                  render={({ field }) => (
                    <FormItem>
                      <label className="mb-1.5 block text-xs text-muted-foreground">
                        What should change?
                      </label>
                      <FormControl>
                        <Textarea
                          {...field}
                          autoFocus
                          placeholder="e.g. Make it harder, add an outcome for interruption handling, rename it to 'Pricing guardrail'…"
                          className="h-48 resize-none text-sm"
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                              event.preventDefault();
                              submit();
                            }
                          }}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
              </>
            )}

            {phase === 'generating' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      {AI_EDIT_STAGES[stageIndex]?.label}
                    </span>
                    <span className="text-xs tabular-nums text-muted-foreground/50">
                      {progress}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-accent">
                    <div
                      className="h-full rounded-full bg-violet-500 transition-all duration-100"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  {AI_EDIT_STAGES.map((stage, i) => {
                    const status =
                      i < stageIndex ? 'done' : i === stageIndex ? 'active' : 'pending';
                    return (
                      <div
                        key={stage.label}
                        className={cn(
                          'flex items-center gap-2 text-[11px] transition-colors',
                          status === 'done' && 'text-muted-foreground',
                          status === 'active' && 'text-foreground',
                          status === 'pending' && 'text-muted-foreground/30',
                        )}
                      >
                        <span
                          className={cn(
                            'h-1.5 w-1.5 shrink-0 rounded-full',
                            status === 'done' && 'bg-violet-400',
                            status === 'active' && 'animate-pulse bg-violet-400',
                            status === 'pending' && 'bg-muted-foreground/20',
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

          {phase === 'input' && (
            <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border px-5 py-4">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                className="h-8 gap-1.5 border-0 bg-violet-600 text-xs text-white hover:bg-violet-500"
                disabled={isPending}
              >
                <Send className="h-3.5 w-3.5" />
                Apply
              </Button>
            </div>
          )}
        </form>
      </Form>
    </div>
  );
}
