'use client';

import { Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { cn } from '@workspace/ui/lib/utils';

import type { ToolParameterValues } from '@/app/(app)/(agent)/_schemas/agent-form';

const PARAM_TYPES = [
  { value: 'string', label: 'String' },
  { value: 'number', label: 'Float' },
  { value: 'integer', label: 'Integer' },
] as const;

interface DraftParameterRowProps {
  param: ToolParameterValues;
  isFirst: boolean;
  nameError?: string;
  onChange: (patch: Partial<ToolParameterValues>) => void;
  onRemove: () => void;
}

export function DraftParameterRow({
  param,
  isFirst,
  nameError,
  onChange,
  onRemove,
}: DraftParameterRowProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-[1.2fr_2fr_100px_36px] items-start px-4 py-2.5 gap-3',
        !isFirst && 'border-t border-border/40'
      )}
    >
      <div className="flex flex-col gap-1">
        <Input
          value={param.name}
          onChange={(event) => onChange({ name: event.target.value })}
          placeholder="param_name"
          aria-invalid={Boolean(nameError)}
          className={cn(
            'h-8 text-xs font-mono bg-accent/20 border-border/60',
            nameError && 'border-red-500/60 focus-visible:ring-red-500/40'
          )}
        />
        {nameError && <span className="text-[10px] text-red-400">{nameError}</span>}
      </div>

      <Input
        value={param.description}
        onChange={(event) => onChange({ description: event.target.value })}
        placeholder="What this parameter does..."
        className="h-8 text-xs bg-accent/20 border-border/60"
      />

      <Select
        value={param.type}
        onValueChange={(value) => onChange({ type: value as 'string' | 'number' | 'integer' })}
      >
        <SelectTrigger className="h-8 text-xs bg-accent/20 border-border/60">
          <SelectValue />
        </SelectTrigger>

        <SelectContent>
          {PARAM_TYPES.map((paramType) => (
            <SelectItem key={paramType.value} value={paramType.value} className="text-xs">
              {paramType.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        variant="ghost"
        size="icon"
        onClick={onRemove}
        className="w-8 h-8 rounded text-muted-foreground/30 hover:text-red-400 hover:bg-red-500/10 transition-colors"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </Button>
    </div>
  );
}
