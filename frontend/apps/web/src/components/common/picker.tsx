'use client';

import { Check, ChevronDown } from 'lucide-react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';
import { cn } from '@workspace/ui/lib/utils';

import type { FC, ReactNode } from 'react';

export interface Option {
  value: string;
  label: string;
}

/** A compact filter or period button with its menu (the Calls and Issues pages). */
export const Picker: FC<{
  label: string;
  value: string | undefined;
  options: Option[];
  onPick: (value: string | undefined) => void;
  icon?: ReactNode;
  align?: 'start' | 'end';
  clearable?: boolean;
  /** Shown as set even when it cannot be cleared, e.g. a status other than its default. */
  highlighted?: boolean;
}> = ({ label, value, options, onPick, icon, align = 'start', clearable = true, highlighted }) => {
  const current = options.find((option) => option.value === value);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border pr-2.5 pl-3 text-body text-ink hover:bg-wash',
          (highlighted ?? (current && clearable))
            ? 'border-ink-secondary bg-wash'
            : 'border-border-control'
        )}
      >
        {icon}
        <span>{current?.label ?? label}</span>
        <ChevronDown className="size-4 text-ink-secondary" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align} className="max-h-[360px] min-w-[220px] overflow-auto">
        {clearable && current && (
          <DropdownMenuItem onSelect={() => onPick(undefined)}>All</DropdownMenuItem>
        )}
        {options.map((option) => (
          <DropdownMenuItem
            key={option.value}
            onSelect={() => onPick(option.value)}
            className="flex items-center justify-between gap-3"
          >
            <span>{option.label}</span>
            {option.value === value && <Check className="size-4" aria-hidden />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
