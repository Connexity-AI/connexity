'use client';

import { Skeleton } from '@workspace/ui/components/ui/skeleton';

export function EvalConfigDetailSkeleton() {
  return (
    <div className="flex flex-1 min-h-0 flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-3.5 w-10" />
          <span className="text-muted-foreground/30">/</span>
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-8 w-16 rounded-md" />
      </div>

      <div className="flex-1 overflow-auto">
        <div className="mx-auto max-w-2xl space-y-4 px-6 py-6">
          <SectionSkeleton fieldCount={2} />
          <SectionSkeleton fieldCount={3} />
          <SectionSkeleton fieldCount={2} />
          <SectionSkeleton fieldCount={1} />
        </div>
      </div>
    </div>
  );
}

function SectionSkeleton({ fieldCount }: { fieldCount: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="flex items-center justify-between border-b border-border bg-accent/10 px-5 py-3">
        <Skeleton className="h-2.5 w-24" />
      </div>
      <div className="space-y-4 px-5 py-4">
        {Array.from({ length: fieldCount }).map((_, index) => (
          <div key={index} className="space-y-1.5">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-9 w-full rounded-md" />
          </div>
        ))}
      </div>
    </div>
  );
}
