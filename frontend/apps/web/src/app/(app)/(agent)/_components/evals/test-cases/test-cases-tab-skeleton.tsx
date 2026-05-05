'use client';

import { Skeleton } from '@workspace/ui/components/ui/skeleton';

export function TestCasesTabSkeleton() {
  return (
    <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-5 py-2.5">
        <Skeleton className="h-3 w-32" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-7 w-32 rounded-md" />
          <Skeleton className="h-7 w-28 rounded-md" />
        </div>
      </div>
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-border px-5">
        <Skeleton className="h-6 w-24 rounded-md" />
        <Skeleton className="h-6 w-28 rounded-md" />
        <Skeleton className="h-6 w-24 rounded-md" />
      </div>
      <div className="grid shrink-0 grid-cols-[32px_minmax(0,1fr)_120px_minmax(0,1fr)] items-center gap-4 border-b border-border bg-background px-5 py-2">
        <Skeleton className="h-3 w-3 rounded" />
        <Skeleton className="h-2 w-12" />
        <Skeleton className="h-2 w-14" />
        <Skeleton className="h-2 w-10" />
      </div>
      <div className="flex-1 overflow-auto">
        <ul>
          {Array.from({ length: 8 }).map((_, index) => (
            <li
              key={index}
              className="grid grid-cols-[32px_minmax(0,1fr)_120px_minmax(0,1fr)] items-center gap-4 border-b border-border/40 px-5 py-2.5"
            >
              <Skeleton className="h-4 w-4 rounded" />
              <Skeleton className="h-3.5 w-56" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-3 w-24" />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
