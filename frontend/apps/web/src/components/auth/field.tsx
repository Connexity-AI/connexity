import { OctagonAlert } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import type { FC, InputHTMLAttributes, ReactNode } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: ReactNode;
  /** The error is announced and carries the critical icon (the reset screens). */
  alert?: boolean;
  /** Sits on the label row, aligned right ("Forgot password?"). */
  labelAction?: ReactNode;
  /** Sits inside the input at its right edge (show or hide the password). */
  trailing?: ReactNode;
}

/** An error line in the critical colour with its icon. */
export const FieldAlert: FC<{ children: ReactNode }> = ({ children }) => (
  <span role="alert" className="flex items-start gap-1.5 text-label text-critical">
    <OctagonAlert aria-hidden className="mt-0.5 size-3.5 flex-none" />
    <span>{children}</span>
  </span>
);

/** A labelled input; an error sits under it in the critical colour. */
export const Field: FC<Props> = ({
  label,
  hint,
  error,
  alert,
  labelAction,
  trailing,
  className,
  ...input
}) => (
  <div className="relative flex flex-col gap-1.5">
    <label className="flex flex-col gap-1.5">
      <span className="text-label text-ink-secondary">{label}</span>
      <input
        {...input}
        aria-invalid={error ? true : undefined}
        className={cn(
          'h-10 rounded-md border bg-surface-1 px-3 text-body text-ink outline-none focus-visible:ring-2 focus-visible:ring-border-control',
          error ? 'border-critical' : 'border-border-control',
          trailing && 'pr-11',
          className
        )}
      />
    </label>
    {labelAction && <span className="absolute top-0 right-0 flex">{labelAction}</span>}
    {trailing && <span className="absolute top-6 right-0 flex">{trailing}</span>}
    {error ? (
      alert ? (
        <FieldAlert>{error}</FieldAlert>
      ) : (
        <span className="text-label text-critical">{error}</span>
      )
    ) : (
      hint && <span className="text-label text-ink-muted">{hint}</span>
    )}
  </div>
);

export default Field;
