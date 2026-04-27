'use client';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { cn } from '@workspace/ui/lib/utils';

import type { ComponentPropsWithoutRef } from 'react';

type CheckboxProps = ComponentPropsWithoutRef<typeof Checkbox>;

/**
 * Shared styling for the eval-run-row / select-all checkboxes so the look
 * and hit area stay in sync between the filter toolbar, the selection
 * toolbar and each result row.
 */
export function SelectionCheckbox({ className, ...props }: CheckboxProps) {
  return (
    <Checkbox
      className={cn(
        'size-4 shrink-0 rounded-[4px] border-[1.5px] transition-colors',
        'border-muted-foreground/40 hover:border-muted-foreground',
        'data-[state=checked]:border-primary data-[state=indeterminate]:border-primary',
        'data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground',
        className,
      )}
      {...props}
    />
  );
}
