'use client';

import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { DraftParameterRow } from '@/app/(app)/(agent)/_components/draft-parameter-row';

import type { ToolParameterValues } from '@/app/(app)/(agent)/_schemas/agent-form';

interface DraftToolParametersProps {
  parameters: ToolParameterValues[];
  onAdd: () => void;
  onUpdate: (index: number, patch: Partial<ToolParameterValues>) => void;
  onRemove: (index: number) => void;
}

export function DraftToolParameters({
  parameters,
  onAdd,
  onUpdate,
  onRemove,
}: DraftToolParametersProps) {
  return (
    <div className="space-y-3">
      {parameters.length > 0 && (
        <div className="rounded-lg border border-border overflow-hidden">
          <div className="grid grid-cols-[1.2fr_2fr_100px_36px] items-center px-4 py-2 bg-accent/30 border-b border-border gap-3">
            <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">
              Name
            </span>

            <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">
              Description
            </span>

            <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">
              Type
            </span>

            <span />
          </div>
          {parameters.map((param, i) => (
            <DraftParameterRow
              key={param.id}
              param={param}
              isFirst={i === 0}
              onChange={(patch) => onUpdate(i, patch)}
              onRemove={() => onRemove(i)}
            />
          ))}
        </div>
      )}

      <Button
        variant="ghost"
        onClick={onAdd}
        className="h-auto p-0 font-normal flex items-center gap-1.5 text-xs text-muted-foreground/50 hover:text-muted-foreground hover:bg-transparent transition-colors py-1"
      >
        <Plus className="w-3.5 h-3.5" />
        Add parameter
      </Button>
    </div>
  );
}
