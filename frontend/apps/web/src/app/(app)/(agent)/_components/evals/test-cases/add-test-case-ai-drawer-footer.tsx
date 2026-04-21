'use client';
'use no memo';

import { Send } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';

import type { AddTestCaseAiValues } from './use-ai-test-case-generation';

interface AddTestCaseAiDrawerFooterProps {
  onCancel: () => void;
}

export function AddTestCaseAiDrawerFooter({ onCancel }: AddTestCaseAiDrawerFooterProps) {
  const form = useFormContext<AddTestCaseAiValues>();
  const promptValue = form.watch('prompt');

  return (
    <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border px-5 py-4">
      <Button type="button" variant="ghost" size="sm" className="h-8 text-xs" onClick={onCancel}>
        Cancel
      </Button>

      <Button
        type="submit"
        size="sm"
        className="h-8 gap-1.5 border-0 bg-violet-600 text-xs text-white hover:bg-violet-500"
        disabled={!promptValue.trim()}
      >
        <Send className="h-3.5 w-3.5" />
        Generate
      </Button>
    </div>
  );
}
