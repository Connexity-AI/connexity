'use client';

import { Skeleton } from '@workspace/ui/components/ui/skeleton';

export function IntegrationsClientSkeleton() {
  return (
    <div className="flex flex-1 flex-col min-w-0 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Skeleton className="h-5 w-28 mb-2" />
          <Skeleton className="h-3.5 w-72" />
        </div>
        <Skeleton className="h-8 w-36 rounded-md" />
      </div>

      <div className="max-w-4xl space-y-8">
        {Array.from({ length: 2 }).map((_, groupIndex) => (
          <div key={groupIndex}>
            <Skeleton className="h-3 w-16 mb-3" />
            <div className="space-y-3">
              {Array.from({ length: 2 }).map((_, cardIndex) => (
                <div
                  key={cardIndex}
                  className="border border-border rounded-lg p-4"
                >
                  <Skeleton className="h-3.5 w-12 mb-2" />
                  <Skeleton className="h-4 w-48 mb-2" />
                  <Skeleton className="h-5 w-40" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
