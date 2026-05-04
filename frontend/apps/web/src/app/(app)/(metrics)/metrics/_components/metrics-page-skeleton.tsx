import { Skeleton } from '@workspace/ui/components/ui/skeleton';

// NOTE: the page header (title + "New metric" button) is rendered by
// the (metrics) route-group layout, so it stays visible during this
// skeleton state — don't duplicate it here.
export function MetricsPageSkeleton() {
  return (
    <div className="flex h-full overflow-hidden bg-background">
      <div className="flex flex-col min-h-0 flex-1">
        <div className="flex items-center justify-between px-5 py-2 border-b border-border shrink-0">
          <Skeleton className="h-3 w-24" />
        </div>

        <div className="flex items-center px-4 py-2 border-b border-border shrink-0 gap-2">
          <Skeleton className="h-7 w-72 rounded-md" />
          <div className="w-px h-4 bg-border shrink-0" />
          <Skeleton className="h-7 w-44 rounded-md" />
        </div>

        <div className="grid grid-cols-[32px_2fr_1fr_1fr_72px] border-b border-border shrink-0 px-5 items-center">
          <div className="py-2">
            <Skeleton className="h-3.5 w-3.5 rounded" />
          </div>
          <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
            Name
          </div>
          <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
            Tier
          </div>
          <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
            Score type
          </div>
          <div className="py-2 text-[10px] text-muted-foreground/50 uppercase tracking-wider">
            Active
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="grid grid-cols-[32px_2fr_1fr_1fr_72px] items-center border-b border-border px-5 min-h-[44px]"
            >
              <Skeleton className="h-3.5 w-3.5 rounded" />
              <div className="py-2.5 pr-4 min-w-0 space-y-1.5">
                <Skeleton className="h-3 w-40" />
                <Skeleton className="h-2.5 w-64" />
              </div>
              <div className="py-2.5 pr-4">
                <Skeleton className="h-4 w-20 rounded" />
              </div>
              <div className="py-2.5">
                <Skeleton className="h-4 w-16 rounded" />
              </div>
              <div className="py-2.5">
                <Skeleton className="h-4 w-7 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
