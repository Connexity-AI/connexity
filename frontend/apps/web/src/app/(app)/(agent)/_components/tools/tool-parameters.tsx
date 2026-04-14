'use client';

import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { ParameterRow } from '@/app/(app)/(agent)/_components/tools/parameter-row';
import { useToolParameters } from '@/app/(app)/(agent)/_hooks/use-tool-parameters';

interface ToolParametersProps {
  toolIndex: number;
}

export function ToolParameters({ toolIndex }: ToolParametersProps) {
  const { fields, addParameter, remove } = useToolParameters(toolIndex);

  return (
    <div className="space-y-3">
      {fields.length > 0 && (
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

          {fields.map((field, paramIndex) => (
            <ParameterRow
              key={field.id}
              toolIndex={toolIndex}
              paramIndex={paramIndex}
              isFirst={paramIndex === 0}
              onRemove={() => remove(paramIndex)}
            />
          ))}
        </div>
      )}

      <Button
        variant="ghost"
        onClick={addParameter}
        className="h-auto p-0 font-normal flex items-center gap-1.5 text-xs text-muted-foreground/50 hover:text-muted-foreground hover:bg-transparent transition-colors py-1"
      >
        <Plus className="w-3.5 h-3.5" />
        Add parameter
      </Button>
    </div>
  );
}
