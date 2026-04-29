'use client';

import { useCallback, useState } from 'react';
import type { DateRange } from 'react-day-picker';

import {
  getPresetRange,
  type DateRangeValue,
  type PresetId,
} from './date-range-picker-utils';

interface UseDateRangePickerParams {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
}

interface UseDateRangePickerResult {
  open: boolean;
  displayRange: DateRange | undefined;
  showEndDateHint: boolean;
  onOpenChange: (open: boolean) => void;
  onPresetSelect: (id: PresetId) => void;
  onCustomSelect: () => void;
  onCalendarSelect: (range: DateRange | undefined) => void;
}

export function useDateRangePicker({
  value,
  onChange,
}: UseDateRangePickerParams): UseDateRangePickerResult {
  const [open, setOpen] = useState(false);
  const [draftRange, setDraftRange] = useState<DateRange | undefined>(undefined);

  const displayRange: DateRange | undefined =
    draftRange ??
    (value.preset === 'custom' ? value.range : getPresetRange(value.preset));

  const onOpenChange = useCallback((next: boolean) => {
    setOpen(next);
    if (!next) setDraftRange(undefined);
  }, []);

  const onPresetSelect = useCallback(
    (id: PresetId) => {
      setDraftRange(undefined);
      onChange({ preset: id, range: getPresetRange(id) });
      setOpen(false);
    },
    [onChange],
  );

  const onCustomSelect = useCallback(() => {
    setDraftRange(undefined);
    onChange({
      preset: 'custom',
      range: { from: undefined, to: undefined },
    });
  }, [onChange]);

  const onCalendarSelect = useCallback(
    (range: DateRange | undefined) => {
      if (!range) return;
      setDraftRange(range);
      if (range.from && range.to) {
        onChange({ preset: 'custom', range });
        setDraftRange(undefined);
      }
    },
    [onChange],
  );

  return {
    open,
    displayRange,
    showEndDateHint: Boolean(draftRange && !draftRange.to),
    onOpenChange,
    onPresetSelect,
    onCustomSelect,
    onCalendarSelect,
  };
}
