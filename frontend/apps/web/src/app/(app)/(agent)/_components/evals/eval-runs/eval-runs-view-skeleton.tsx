import { Skeleton } from '@workspace/ui/components/ui/skeleton';

export function EvalRunsViewSkeleton() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-5 py-2.5">
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-border px-4 py-2">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-7 w-40" />
      </div>
      <div className="sticky top-0 z-10 grid grid-cols-[32px_1fr_72px_110px_110px_96px] items-center gap-3 border-b border-border bg-background px-5 py-2 text-[10px] uppercase tracking-wider text-muted-foreground/60">
        <span />
        <span>Run</span>
        <span>Tool Calls</span>
        <span>Score</span>
        <span>Cases</span>
        <span aria-hidden="true" />
      </div>
      <ul>
        {Array.from({ length: 8 }).map((_, i) => (
          <li
            key={i}
            className="grid grid-cols-[32px_1fr_72px_110px_110px_96px] items-center gap-3 border-b border-border/40 px-5 py-3"
          >
            <Skeleton className="h-4 w-4" />
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-3.5 w-56" />
              <Skeleton className="h-3 w-32" />
            </div>
            <Skeleton className="h-4 w-10" />
            <Skeleton className="h-3 w-14" />
            <Skeleton className="h-3 w-14" />
            <Skeleton className="h-3 w-16 justify-self-end" />
          </li>
        ))}
      </ul>
    </div>
  );
}
