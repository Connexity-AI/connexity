'use client';

import { Brain } from 'lucide-react';

import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { Textarea } from '@workspace/ui/components/ui/textarea';

interface AddTestCaseAiInputPhaseProps {
  error: string | null;
}

export function AddTestCaseAiInputPhase({ error }: AddTestCaseAiInputPhaseProps) {
  return (
    <>
      <div className="mb-4 flex items-start gap-2 rounded-lg border border-violet-500/20 bg-violet-500/5 px-3 py-2.5">
        <Brain className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />

        <p className="text-[11px] leading-snug text-violet-300/80">
          AI will read your <span className="text-violet-300">agent prompt</span> to generate test
          case(s)
        </p>
      </div>

      <FormField
        name="prompt"
        render={({ field }) => (
          <FormItem>
            <label className="mb-1.5 block text-xs text-muted-foreground">
              What should this test case cover?
            </label>
            <FormControl>
              <Textarea
                {...field}
                placeholder="e.g. A customer who gives an out-of-scope request about pricing, the agent should politely decline and redirect to scheduling…"
                className="h-48 resize-none text-sm"
              />
            </FormControl>

            <FormMessage />

            <p className="mt-1.5 text-[10px] text-muted-foreground/40">
              You can generate multiple test cases
            </p>
          </FormItem>
        )}
      />

      {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
    </>
  );
}
