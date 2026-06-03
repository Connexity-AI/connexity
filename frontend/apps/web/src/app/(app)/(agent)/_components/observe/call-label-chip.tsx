'use client';

import { CheckCircle2, AlertTriangle } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { CallLabel } from '@/client/types.gen';

interface CallLabelChipProps {
  label: CallLabel | null;
  className?: string;
}

export function CallLabelChip({ label, className }: CallLabelChipProps) {
  if (label === null) {
    return <span className="text-[10px] text-muted-foreground/30">—</span>;
  }

  const isGood = label === CallLabel.GOOD;
  const Icon = isGood ? CheckCircle2 : AlertTriangle;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border px-1.5 py-px align-middle text-[10px]',
        isGood
          ? 'border-emerald-500/25 bg-emerald-500/15 text-emerald-300'
          : 'border-rose-500/30 bg-rose-500/15 text-rose-300',
        className,
      )}
    >
      <Icon className="h-2.5 w-2.5" />
      {isGood ? 'Good' : 'Bad'}
    </span>
  );
}
