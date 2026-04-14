'use client';

import { useState } from 'react';

import { Eye, EyeOff, Trash2 } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';

interface DraftAuthHeaderRowProps {
  header: { key: string; value: string };
  onChange: (patch: { key?: string; value?: string }) => void;
  onRemove: () => void;
}

export function DraftAuthHeaderRow({ header, onChange, onRemove }: DraftAuthHeaderRowProps) {
  const [showValue, setShowValue] = useState(false);

  return (
    <div className="flex items-center gap-2">
      <Input
        value={header.key}
        onChange={(event) => onChange({ key: event.target.value })}
        placeholder="Header key"
        className="h-8 text-xs font-mono bg-accent/20 border-border/60 flex-2"
      />

      <div className="relative flex-3">
        <Input
          type={showValue ? 'text' : 'password'}
          value={header.value}
          onChange={(event) => onChange({ value: event.target.value })}
          placeholder="Value"
          className="h-8 text-xs font-mono bg-accent/20 border-border/60 pr-8"
        />

        <Button
          variant="ghost"
          onClick={() => setShowValue((current) => !current)}
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
