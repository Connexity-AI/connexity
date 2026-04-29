'use client';

import { useState } from 'react';

import { Plus, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';

interface SetAllRunsProps {
  casesCount: number;
  onApply: (value: number) => void;
}

function SetAllRuns({ casesCount, onApply }: SetAllRunsProps) {
  const [expanded, setExpanded] = useState(false);
  const [value, setValue] = useState(1);

  if (casesCount === 0) return null;

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="cursor-pointer text-xs text-muted-foreground/60 transition-colors hover:text-foreground"
      >
        Set all
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-muted-foreground">Set all to</span>

      <Input
        type="number"
        min={1}
        max={100}
        value={value}
        onChange={(e) => setValue(Math.max(1, Number(e.target.value) || 1))}
        className="h-7 w-16 text-xs"
      />

      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-7 text-xs"
        onClick={() => {
          onApply(value);
          setExpanded(false);
        }}
      >
        Apply
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={() => setExpanded(false)}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
}

interface TestCasesHeaderActionsProps {
  readOnly: boolean;
  casesCount: number;
  onOpenPicker: () => void;
  onSetAll: (value: number) => void;
}

export function TestCasesHeaderActions({
  readOnly,
  casesCount,
  onOpenPicker,
  onSetAll,
}: TestCasesHeaderActionsProps) {
  if (readOnly) return null;

  return (
    <div className="flex items-center gap-3">
      <SetAllRuns casesCount={casesCount} onApply={onSetAll} />
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-7 gap-1.5 text-xs"
        onClick={onOpenPicker}
      >
        <Plus className="h-3 w-3" />
        Add
      </Button>
    </div>
  );
}
