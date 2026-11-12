import { cn } from '@workspace/ui/lib/utils';

import type { FC, InputHTMLAttributes, ReactNode } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: ReactNode;
}

/** A labelled input; an error sits under it in the critical colour. */
export const Field: FC<Props> = ({ label, hint, error, className, ...input }) => (
  <label className="flex flex-col gap-1.5">
    <span className="text-label text-ink-secondary">{label}</span>
    <input
      {...input}
      aria-invalid={error ? true : undefined}
      className={cn(
        'h-10 rounded-md border bg-surface-1 px-3 text-body text-ink outline-none focus-visible:ring-2 focus-visible:ring-border-control',
        error ? 'border-critical' : 'border-border-control',
        className
      )}
    />
    {error ? (
      <span className="text-label text-critical">{error}</span>
    ) : (
      hint && <span className="text-label text-ink-muted">{hint}</span>
    )}
  </label>
);

export default Field;
