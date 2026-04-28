'use client';

import { LlmModelPicker } from '@/app/(app)/(agent)/_components/llm/llm-model-picker';

interface ModelSelectorProps {
  model: string;
  onModelChange: (model: string) => void;
  disabled?: boolean;
}

/**
 * Compact assistant-model picker sized to sit inside the chat-input toolbar.
 */
export function ModelSelector({ model, onModelChange, disabled }: ModelSelectorProps) {
  return (
    <LlmModelPicker
      value={model}
      onSelect={(modelOption) => onModelChange(modelOption.id)}
      disabled={disabled}
      compact
      align="end"
      triggerClassName="border-border bg-transparent focus:ring-1 focus:ring-ring focus:ring-offset-0"
    />
  );
}
