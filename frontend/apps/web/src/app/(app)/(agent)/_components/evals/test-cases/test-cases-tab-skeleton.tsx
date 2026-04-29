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
      <div className="flex-1 overflow-auto">
        <ul>
          {Array.from({ length: 8 }).map((_, index) => (
            <li
              key={index}
              className="flex items-center gap-4 border-b border-border/40 px-5 py-3"
            >
              <Skeleton className="h-4 w-4 rounded" />
              <Skeleton className="h-3.5 w-56" />
              <Skeleton className="ml-auto h-3 w-20" />
              <Skeleton className="h-3 w-16" />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
