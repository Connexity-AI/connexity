'use client';

import { Loader2, Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import type { TestCasePublic } from '@/client/types.gen';

interface TestCaseDrawerFooterProps {
  testCase: TestCasePublic | null;
  isPending: boolean;
  onRequestDelete: (testCase: TestCasePublic) => void;
}

export function TestCaseDrawerFooter({
  testCase,
  isPending,
  onRequestDelete,
}: TestCaseDrawerFooterProps) {
  const handleDelete = () => {
    if (testCase) onRequestDelete(testCase);
  };

  return (
    <div className="flex shrink-0 items-center justify-between border-t border-border px-4 py-3">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={handleDelete}
        className="h-7 gap-1.5 px-2 text-xs text-red-400/70 hover:bg-transparent hover:text-red-400"
      >
        <Trash2 className="h-3.5 w-3.5" />
        Delete
      </Button>

      <Button type="submit" size="sm" className="h-7 gap-1.5 text-xs" disabled={isPending}>
        {isPending && <Loader2 className="h-3 w-3 animate-spin" />}
        Save changes
      </Button>
    </div>
  );
}
