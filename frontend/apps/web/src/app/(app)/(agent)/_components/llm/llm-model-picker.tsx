'use client';

import { Check, ChevronsUpDown, CircleHelp, Loader2 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@workspace/ui/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@workspace/ui/components/ui/popover';
import { cn } from '@workspace/ui/lib/utils';

import { useLlmModels } from '@/app/(app)/(agent)/_hooks/use-llm-models';

import type { LlmModelProviderPublic, LlmModelPublic } from '@/client/types.gen';

export type LlmModelSelection = Pick<
  LlmModelPublic,
  'id' | 'provider' | 'provider_label' | 'model' | 'label'
>;

interface LlmModelPickerProps {
  value?: string | null;
  provider?: string | null;
  onSelect: (model: LlmModelSelection) => void;
  disabled?: boolean;
  placeholder?: string;
  align?: 'start' | 'center' | 'end';
  triggerClassName?: string;
  contentClassName?: string;
  compact?: boolean;
}

const MODELS_PER_PROVIDER = 5;

export function LlmModelPicker({
  value,
  provider,
  onSelect,
  disabled,
  placeholder = 'Select model',
  align = 'start',
  triggerClassName,
  contentClassName,
  compact = false,
}: LlmModelPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const { data: catalog, isFetching } = useLlmModels();
  const selectedModel = useMemo(
    () => findModel(catalog.data, value, provider),
    [catalog.data, value, provider]
  );
  const visibleProviders = useMemo(
    () => visibleProviderGroups(catalog.data, search),
    [catalog.data, search]
  );
  const selectedId = selectedModel?.id;
  const displayValue = selectedModel ? selectedModel.model : value || placeholder;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label="LLM model"
          disabled={disabled}
          className={cn(
            'justify-between gap-2 border-input bg-background font-normal',
            compact ? 'h-7 w-auto px-2 text-xs' : 'h-9 w-full text-sm',
            triggerClassName
          )}
        >
          <span className="min-w-0 truncate" suppressHydrationWarning>
            {displayValue || placeholder}
          </span>
          {isFetching ? (
            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin opacity-60" />
          ) : (
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-50" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align={align}
        className={cn(
          compact ? 'w-[320px]' : 'w-[var(--radix-popover-trigger-width)]',
          'p-0',
          contentClassName
        )}
      >
        <Command>
          <CommandInput
            value={search}
            onValueChange={setSearch}
            placeholder="Search models..."
          />
          <CommandList>
            <CommandEmpty>No models found.</CommandEmpty>
            {visibleProviders.map((providerGroup) => (
              <CommandGroup key={providerGroup.provider} heading={providerGroup.label}>
                {providerGroup.models.map((model) => (
                  <CommandItem
                    key={model.id}
                    value={`${model.id} ${model.model} ${model.provider}`}
                    onSelect={() => {
                      onSelect(model);
                      setOpen(false);
                      setSearch('');
                    }}
                    className="items-start"
                  >
                    <Check
                      className={cn(
                        'mt-0.5 h-4 w-4',
                        selectedId === model.id ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-mono text-xs">{model.model}</div>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
          <div className="flex items-start gap-2 border-t px-3 py-2 text-[11px] leading-4 text-muted-foreground">
            <CircleHelp className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>Add provider API keys to the backend environment to list more models.</span>
          </div>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

function visibleProviderGroups(
  providers: LlmModelProviderPublic[],
  search: string
): LlmModelProviderPublic[] {
  if (search.trim()) return providers;

  return providers
    .map((provider) => {
      const models = provider.models.slice(0, MODELS_PER_PROVIDER);
      return { ...provider, models };
    })
    .filter((provider) => provider.models.length > 0);
}

function findModel(
  providers: LlmModelProviderPublic[],
  value?: string | null,
  provider?: string | null
): LlmModelPublic | undefined {
  if (!value) return undefined;

  const allModels = providers.flatMap((providerGroup) => providerGroup.models);
  const exact = allModels.find((model) => model.id === value);
  if (exact) return exact;

  const providerKey = normalizeProvider(provider);
  return allModels.find((model) => {
    const matchesProvider =
      !providerKey ||
      model.provider.toLowerCase() === providerKey ||
      model.provider_label.toLowerCase() === providerKey;
    return matchesProvider && model.model === value;
  });
}

function normalizeProvider(provider?: string | null): string | null {
  const normalized = provider?.trim().toLowerCase();
  return normalized || null;
}
