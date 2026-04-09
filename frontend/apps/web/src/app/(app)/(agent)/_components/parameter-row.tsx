'use client';

import { useFormContext } from 'react-hook-form';
import { Trash2 } from 'lucide-react';
import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';
import { cn } from '@workspace/ui/lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

const PARAM_TYPES = [
  { value: 'string', label: 'String' },
  { value: 'number', label: 'Number' },
  { value: 'integer', label: 'Integer' },
] as const;

interface ParameterRowProps {
  toolIndex: number;
  paramIndex: number;
  isFirst: boolean;
  onRemove: () => void;
}

export function ParameterRow({ toolIndex, paramIndex, isFirst, onRemove }: ParameterRowProps) {
  const { register, watch, setValue } = useFormContext<AgentFormValues>();

  const basePath = `tools.${toolIndex}.parameters.${paramIndex}` as const;
  const type = watch(`${basePath}.type`);

  return (
    <div
      className={cn(
        'grid grid-cols-[1.2fr_2fr_100px_36px] items-center px-4 py-2.5 gap-3',
        !isFirst && 'border-t border-border/40'
      )}
    >
      <Input
        {...register(`${basePath}.name`)}
        placeholder="param_name"
        className="h-8 text-xs font-mono bg-accent/20 border-border/60"
      />

      <Input
        {...register(`${basePath}.description`)}
        placeholder="What this parameter does..."
        className="h-8 text-xs bg-accent/20 border-border/60"
      />

      <Select value={type} onValueChange={(v) => setValue(`${basePath}.type`, v as 'string' | 'number' | 'integer')}>
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
