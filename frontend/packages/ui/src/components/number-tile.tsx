import { cn } from '@workspace/ui/lib/utils';

import { SEVERITY } from './severity';

import type { LucideIcon } from 'lucide-react';
import type { FC, ReactNode } from 'react';
import type { Severity } from './severity';

interface Props {
  /** One bare noun: "Calls", "Issues", "Latency". */
  label: string;
  value: ReactNode;
  /** A unit after the value, such as "s". */
  unit?: string;
  /** Only for a state; the label then carries the state's icon. */
  severity?: Severity;
  /** A neutral icon before the label, for a count that is not a state ("Not graded"). */
  icon?: LucideIcon;
}

/** A label and a value, nothing else (Connexity Design System, number tile). */
export const NumberTile: FC<Props> = ({ label, value, unit, severity, icon }) => {
  const state = severity ? SEVERITY[severity] : undefined;
  const Icon = state?.icon ?? icon;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-hairline bg-surface-1 p-4">
      <span
        className={cn(
          'flex items-center gap-1.5 text-label',
          state ? state.text : 'text-ink-secondary'
        )}
      >
        {Icon && <Icon className="size-3.5" aria-hidden />}
        {label}
      </span>
      <span className={cn('text-tile font-medium', state ? state.text : 'text-ink')}>
        {value}
        {unit && <span className="text-title text-ink-secondary"> {unit}</span>}
      </span>
    </div>
  );
};

export default NumberTile;
