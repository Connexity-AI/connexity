'use client';

import { useState } from 'react';

import { Eye, EyeOff, Trash2 } from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

interface AuthHeaderRowProps {
  toolIndex: number;
  headerIndex: number;
  onRemove: () => void;
}

export function AuthHeaderRow({ toolIndex, headerIndex, onRemove }: AuthHeaderRowProps) {
  const [showValue, setShowValue] = useState(false);
  const { register } = useFormContext<AgentFormValues>();

  const basePath = `tools.${toolIndex}.authHeaders.${headerIndex}` as const;

  return (
    <div className="flex items-center gap-2">
      <Input
        {...register(`${basePath}.key`)}
        placeholder="Header key"
        className="h-8 text-xs font-mono bg-accent/20 border-border/60 flex-2"
      />

      <div className="relative flex-3">
        <Input
          type={showValue ? 'text' : 'password'}
          {...register(`${basePath}.value`)}
          placeholder="Value"
          className="h-8 text-xs font-mono bg-accent/20 border-border/60 pr-8"
        />

        <Button
          variant="ghost"
          onClick={() => setShowValue((s) => !s)}
          className="h-auto p-0 absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/30 hover:text-muted-foreground hover:bg-transparent transition-colors"
        >
          {showValue ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
        </Button>
      </div>

      <Button
        variant="ghost"
        size="icon"
        onClick={onRemove}
        className="shrink-0 w-8 h-8 rounded text-muted-foreground/30 hover:text-red-400 hover:bg-red-500/10 transition-colors"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </Button>
    </div>
  );
}
