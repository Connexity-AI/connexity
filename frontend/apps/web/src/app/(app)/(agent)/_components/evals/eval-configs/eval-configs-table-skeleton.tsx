'use client';

import { Skeleton } from '@workspace/ui/components/ui/skeleton';

export function EvalConfigsTableSkeleton() {
  return (
    <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-5 py-2.5">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-7 w-36 rounded-md" />
      </div>
      <div className="flex-1 overflow-auto">
        <div className="sticky top-0 z-10 grid grid-cols-[1fr_120px_120px_80px_180px] items-center gap-4 border-b border-border bg-background px-5 py-2 text-[10px] uppercase tracking-wider text-muted-foreground/60">
          <span>Name</span>
          <span>Test Cases</span>
          <span>Runs</span>
          <span>Version</span>
          <span>Updated</span>
        </div>
        <ul>
          {Array.from({ length: 6 }).map((_, index) => (
            <li
              key={index}
              className="grid grid-cols-[1fr_120px_120px_80px_180px] items-center gap-4 border-b border-border/40 px-5 py-2.5"
            >
              <Skeleton className="h-3.5 w-48" />
              <Skeleton className="h-3 w-8" />
              <Skeleton className="h-3 w-8" />
              <Skeleton className="h-3 w-6" />
              <Skeleton className="h-3 w-32" />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
