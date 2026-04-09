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
  { value: 'number', label: 'Number' },
  { value: 'integer', label: 'Integer' },
] as const;

interface DraftParameterRowProps {
  param: ToolParameterValues;
  isFirst: boolean;
  onChange: (patch: Partial<ToolParameterValues>) => void;
  onRemove: () => void;
}

export function DraftParameterRow({ param, isFirst, onChange, onRemove }: DraftParameterRowProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-[1.2fr_2fr_100px_36px] items-center px-4 py-2.5 gap-3',
        !isFirst && 'border-t border-border/40'
      )}
    >
      <Input
        value={param.name}
        onChange={(e) => onChange({ name: e.target.value })}
        placeholder="param_name"
        className="h-8 text-xs font-mono bg-accent/20 border-border/60"
      />

      <Input
        value={param.description}
        onChange={(e) => onChange({ description: e.target.value })}
        placeholder="What this parameter does..."
        className="h-8 text-xs bg-accent/20 border-border/60"
      />

      <Select
        value={param.type}
        onValueChange={(v) => onChange({ type: v as 'string' | 'number' | 'integer' })}
      >
        <SelectTrigger className="h-8 text-xs bg-accent/20 border-border/60">
          <SelectValue />
        </SelectTrigger>

        <SelectContent>
          {PARAM_TYPES.map((t) => (
            <SelectItem key={t.value} value={t.value} className="text-xs">
              {t.label}
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
