import { format, startOfToday, subDays } from 'date-fns';
import type { DateRange } from 'react-day-picker';

export type PresetId = 'today' | '7d' | '14d' | '30d' | '90d' | 'custom';

export interface DateRangeValue {
  preset: PresetId;
  range: DateRange;
}

export const PRESETS: { id: Exclude<PresetId, 'custom'>; label: string }[] = [
  { id: 'today', label: 'Today' },
  { id: '7d', label: 'Last 7 days' },
  { id: '14d', label: 'Last 14 days' },
  { id: '30d', label: 'Last 30 days' },
  { id: '90d', label: 'Last 90 days' },
];

export function getPresetRange(preset: PresetId): DateRange {
  const today = startOfToday();
  const now = new Date();
  switch (preset) {
    case 'today':
      return { from: today, to: now };
    case '7d':
      return { from: subDays(today, 6), to: now };
    case '14d':
      return { from: subDays(today, 13), to: now };
    case '30d':
      return { from: subDays(today, 29), to: now };
    case '90d':
      return { from: subDays(today, 89), to: now };
    default:
      return { from: undefined, to: undefined };
  }
}

export const DEFAULT_DATE_RANGE: DateRangeValue = {
  preset: '7d',
  range: getPresetRange('7d'),
};

export function formatLabel(value: DateRangeValue): string {
  if (value.preset !== 'custom') {
    return PRESETS.find((p) => p.id === value.preset)?.label ?? 'Select range';
  }
  const { from, to } = value.range;
  if (!from) return 'Custom range';
  if (!to) return format(from, 'MMM d, yyyy');
  return `${format(from, 'MMM d')} – ${format(to, 'MMM d, yyyy')}`;
}
