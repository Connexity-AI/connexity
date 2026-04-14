import { cn } from '@workspace/ui/lib/utils';

export function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] text-muted-foreground/50 uppercase tracking-widest mb-3 pb-2 border-b border-border/50">
      {children}
    </p>
  );
}

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label className="text-xs text-muted-foreground">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground/40 leading-relaxed">{hint}</p>}
    </div>
  );
}
