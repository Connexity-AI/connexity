'use client';

import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
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

import { useTtsVoices } from '@/app/(app)/(agent)/_hooks/use-tts-voices';

interface TtsVoicePickerProps {
  provider: string;
  model: string;
  value?: string | null;
  onSelect: (voiceId: string, label: string) => void;
  disabled?: boolean;
}

export function TtsVoicePicker({
  provider,
  model,
  value,
  onSelect,
  disabled,
}: TtsVoicePickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const { data: catalog, isFetching } = useTtsVoices(provider, model);

  const selectedVoice = useMemo(
    () => catalog.data.find((voice) => voice.id === value),
    [catalog.data, value]
  );

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return catalog.data;
    return catalog.data.filter(
      (voice) =>
        voice.id.toLowerCase().includes(term) || voice.label.toLowerCase().includes(term)
    );
  }, [catalog.data, search]);

  const pickerDisabled = disabled || !provider.trim() || !model.trim();
  const placeholder = !provider.trim() || !model.trim() ? 'Select TTS model first' : 'Select voice';
  const displayValue = selectedVoice?.label ?? value ?? placeholder;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label="TTS voice"
          disabled={pickerDisabled}
          className="h-9 w-full justify-between gap-2 border-input bg-background font-normal text-sm"
        >
          <span className="min-w-0 truncate" suppressHydrationWarning>
            {displayValue}
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
            placeholder="Search voices..."
          />
          <CommandList>
            <CommandEmpty>No voices found.</CommandEmpty>
            <CommandGroup>
              {filtered.map((voice, index) => (
                <CommandItem
                  key={`${voice.id}:${index}`}
                  value={`${voice.id} ${voice.label}`}
                  onSelect={() => {
                    onSelect(voice.id, voice.label);
                    setOpen(false);
                    setSearch('');
                  }}
                >
                  <Check
                    className={cn(
                      'h-4 w-4',
                      value === voice.id ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                  <span className="truncate text-xs">{voice.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
