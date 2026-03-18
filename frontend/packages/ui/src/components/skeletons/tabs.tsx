import { Skeleton } from '@workspace/ui/components/ui/skeleton';

import type { FC } from 'react';

interface TabsSkeletonProps {
  tabs?: number;
  blocks?: number;
}

// unused
const TabsSkeleton: FC<TabsSkeletonProps> = ({ tabs = 3, blocks = 1 }) => {
  return (
    <div className="space-y-6">
      {/* Tabs Header */}
      <div className="flex gap-6 bg-secondary/40 p-2 rounded-lg">
        {Array.from({ length: tabs }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-28 rounded-md" />
        ))}
      </div>

      {/* Generic Content */}
      {Array.from({ length: blocks }).map((_, i) => (
        <div key={i} className="border shadow-sm rounded-md p-6">
          <Skeleton className="h-64 w-full rounded-md" />
        </div>
      ))}
    </div>
  );
};

export default TabsSkeleton;
