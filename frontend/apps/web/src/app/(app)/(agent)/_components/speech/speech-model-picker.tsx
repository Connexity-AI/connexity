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

import type { SpeechModelProviderPublic, SpeechModelPublic } from '@/client/types.gen';

export type SpeechModelSelection = Pick<
  SpeechModelPublic,
  'id' | 'provider' | 'provider_label' | 'model' | 'label'
>;

interface SpeechModelPickerProps {
  catalog: SpeechModelProviderPublic[];
  isFetching?: boolean;
  value?: string | null;
  provider?: string | null;
  onSelect: (model: SpeechModelSelection) => void;
  disabled?: boolean;
  placeholder?: string;
  ariaLabel?: string;
  hint?: string;
}

const MODELS_PER_PROVIDER = 5;

export function SpeechModelPicker({
  catalog,
  isFetching = false,
  value,
  provider,
  onSelect,
  disabled,
  placeholder = 'Select model',
  ariaLabel = 'Speech model',
  hint = 'Add provider API keys to the backend environment to list more models.',
}: SpeechModelPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const selectedModel = useMemo(
    () => findModel(catalog, value, provider),
    [catalog, value, provider]
  );
  const visibleProviders = useMemo(
    () => visibleProviderGroups(catalog, search),
    [catalog, search]
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
          aria-label={ariaLabel}
          disabled={disabled}
          className="h-9 w-full justify-between gap-2 border-input bg-background font-normal text-sm"
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
      <PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] p-0">
        <Command>
          <CommandInput
            value={search}
            onValueChange={setSearch}
            placeholder="Search models..."
          />
          <CommandList>
            <CommandEmpty>No models found.</CommandEmpty>
            {visibleProviders.map((providerGroup) => (
              <CommandGroup
                key={`${providerGroup.provider}:${providerGroup.label}`}
                heading={providerGroup.label}
              >
                {uniqueModels(providerGroup.models).map((model, index) => (
                  <CommandItem
                    key={`${providerGroup.provider}:${model.id}:${index}`}
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
            <span>{hint}</span>
          </div>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

function uniqueModels(models: SpeechModelPublic[]): SpeechModelPublic[] {
  const seen = new Set<string>();
  return models.filter((model) => {
    if (seen.has(model.id)) {
      return false;
    }
    seen.add(model.id);
    return true;
  });
}

function visibleProviderGroups(
  providers: SpeechModelProviderPublic[],
  search: string
): SpeechModelProviderPublic[] {
  const groups = providers.map((providerGroup) => ({
    ...providerGroup,
    models: uniqueModels(providerGroup.models),
  }));

  if (search.trim()) {
    return groups.filter((providerGroup) => providerGroup.models.length > 0);
  }

  return groups
    .map((providerGroup) => {
      const models = providerGroup.models.slice(0, MODELS_PER_PROVIDER);
      return { ...providerGroup, models };
    })
    .filter((providerGroup) => providerGroup.models.length > 0);
}

function findModel(
  providers: SpeechModelProviderPublic[],
  value?: string | null,
  provider?: string | null
): SpeechModelPublic | undefined {
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
