'use client';

import { CalendarIcon, ChevronDown } from 'lucide-react';

import { Calendar } from '@workspace/ui/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@workspace/ui/components/ui/popover';
import { cn } from '@workspace/ui/lib/utils';

import {
  formatLabel,
  PRESETS,
  type DateRangeValue,
} from './date-range-picker-utils';
import { useDateRangePicker } from './use-date-range-picker';

interface Props {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
}

export function DateRangePicker({ value, onChange }: Props) {
  const {
    open,
    displayRange,
    showEndDateHint,
    onOpenChange,
    onPresetSelect,
    onCustomSelect,
    onCalendarSelect,
  } = useDateRangePicker({ value, onChange });

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            'flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[11px] transition-colors',
            open
              ? 'border-violet-500/40 bg-violet-500/10 text-violet-300'
              : 'border-border bg-background text-muted-foreground hover:bg-accent/30',
          )}
        >
          <CalendarIcon className="h-3.5 w-3.5 shrink-0" />
          <span className="whitespace-nowrap">{formatLabel(value)}</span>
          <ChevronDown
            className={cn(
              'h-3 w-3 opacity-50 transition-transform',
              open && 'rotate-180',
            )}
          />
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="flex w-auto overflow-hidden rounded-xl border border-border p-0 shadow-xl"
      >
        <div className="flex w-36 shrink-0 flex-col border-r border-border py-2">
          <p className="px-4 pb-2 pt-1 text-[9px] uppercase tracking-wider text-muted-foreground/40">
            Quick select
          </p>
          {PRESETS.map((preset) => {
            const active = value.preset === preset.id;
            return (
              <button
                type="button"
                key={preset.id}
                onClick={() => onPresetSelect(preset.id)}
                className={cn(
                  'px-4 py-1.5 text-left text-[12px] transition-colors',
                  active
                    ? 'bg-violet-500/10 text-violet-300'
                    : 'text-muted-foreground hover:bg-accent/20 hover:text-foreground',
                )}
              >
                {active && <span className="mr-1.5 text-violet-400">·</span>}
                {preset.label}
              </button>
            );
          })}
          <div className="my-2 border-t border-border" />
          <button
            type="button"
            onClick={onCustomSelect}
            className={cn(
              'px-4 py-1.5 text-left text-[12px] transition-colors',
              value.preset === 'custom'
                ? 'bg-violet-500/10 text-violet-300'
                : 'text-muted-foreground hover:bg-accent/20 hover:text-foreground',
            )}
          >
            {value.preset === 'custom' && (
              <span className="mr-1.5 text-violet-400">·</span>
            )}
            Custom range
          </button>
        </div>

        <div className="p-3">
          {showEndDateHint && (
            <p className="mb-1 text-center text-[10px] text-muted-foreground/60">
              Pick an end date
            </p>
          )}
          <Calendar
            mode="range"
            selected={displayRange}
            onSelect={onCalendarSelect}
            numberOfMonths={2}
            disabled={{ after: new Date() }}
          />
        </div>
      </PopoverContent>
    </Popover>
  );
}
