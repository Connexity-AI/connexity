'use client';

import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

interface TestCasesEmptyProps {
  readOnly: boolean;
  onOpenPicker: () => void;
}

function EmptyMessage({ readOnly }: { readOnly: boolean }) {
  if (readOnly) {
    return (
      <p className="text-xs text-muted-foreground/60">No test cases in this config</p>
    );
  }

  return <p className="text-xs text-muted-foreground/60">No test cases selected yet</p>;
}

function AddTestCasesButton({ readOnly, onOpenPicker }: TestCasesEmptyProps) {
  if (readOnly) return null;

  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      className="h-7 gap-1.5 text-xs"
      onClick={onOpenPicker}
    >
      <Plus className="h-3 w-3" />
      Add test cases
    </Button>
  );
}

export function TestCasesEmpty({ readOnly, onOpenPicker }: TestCasesEmptyProps) {
  return (
    <div className="flex flex-col items-center gap-2 py-8">
      <EmptyMessage readOnly={readOnly} />
      <AddTestCasesButton readOnly={readOnly} onOpenPicker={onOpenPicker} />
    </div>
  );
}
