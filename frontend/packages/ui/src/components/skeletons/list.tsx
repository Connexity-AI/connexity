import { Skeleton } from '@workspace/ui/components/ui/skeleton';

import type { FC } from 'react';

// Todo: improve paddings, props and responsiveness

export const ListItemSkeleton: FC = () => (
  <div className="flex items-center justify-between rounded-md">
    <div className="space-y-2">
      <Skeleton className="h-3 w-48" />
      <Skeleton className="h-3 w-32" />
    </div>
    <Skeleton className="h-6 w-16 rounded-full" />
  </div>
);

const ListHeaderSkeleton: FC = () => (
  <div className="flex justify-between items-center mb-4">
    <div className="flex items-center space-x-3">
      <Skeleton className="size-10 rounded-full" />
      <Skeleton className="h-4 w-32" />
    </div>
    <Skeleton className="h-4 w-16" />
  </div>
);

interface ListSkeletonProps {
  count?: number;
  showHeader?: boolean;
}

export const ListSkeleton: FC<ListSkeletonProps> = ({ count = 1, showHeader = true }) => {
  return (
    <div className="space-y-4 border shadow-sm rounded-md p-4">
      {showHeader && <ListHeaderSkeleton />}
      {Array.from({ length: count }).map((_, i) => (
        <ListItemSkeleton key={i} />
      ))}
    </div>
  );
};

export default ListSkeleton;
