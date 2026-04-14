'use client';

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';

import { ASSISTANT_MODELS } from '@/config/assistant-models';

interface ModelSelectorProps {
  model: string;
  onModelChange: (model: string) => void;
  disabled?: boolean;
}

/**
 * Compact assistant-model picker using the shared shadcn `Select`. Sized to
 * sit inside the chat-input toolbar (overrides the trigger's default `h-10`).
 * Options are grouped by provider — source of truth is
 * `src/config/assistant-models.json`.
 */
export function ModelSelector({ model, onModelChange, disabled }: ModelSelectorProps) {
  return (
    <Select value={model} onValueChange={onModelChange} disabled={disabled}>
      <SelectTrigger
        aria-label="Assistant model"
        className="h-7 w-auto gap-1.5 px-2 text-xs border-border bg-transparent focus:ring-1 focus:ring-ring focus:ring-offset-0 [&>svg]:h-3 [&>svg]:w-3"
      >
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="end" className="min-w-40">
        {ASSISTANT_MODELS.groups.map((group) => (
          <SelectGroup key={group.label}>
            <SelectLabel className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
              {group.label}
            </SelectLabel>

            {group.models.map((modelOption) => (
              <SelectItem key={modelOption.id} value={modelOption.id} className="text-xs">
                {modelOption.label}
              </SelectItem>
            ))}
          </SelectGroup>
        ))}
      </SelectContent>
    </Select>
  );
}
