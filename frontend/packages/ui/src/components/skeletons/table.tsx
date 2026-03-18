import { Skeleton } from '@workspace/ui/components/ui/skeleton';
import { cn } from '@workspace/ui/lib/utils';

import type { FC } from 'react';

export const TableRowSkeleton: FC = () => (
  <div className="flex justify-between items-center space-x-4">
    <Skeleton className="h-4 w-16" />
    <Skeleton className="h-4 w-32" />
    <Skeleton className="h-4 w-48" />
    <Skeleton className="h-4 w-20" />
    <Skeleton className="h-4 w-20" />
  </div>
);

interface TableHeaderSkeletonProps {
  className?: string;
}

const TableHeaderSkeleton: FC<TableHeaderSkeletonProps> = ({ className }) => (
  <div className={cn('flex justify-between items-center', className)}>
    <div className="flex items-center space-x-3">
      <Skeleton className="size-10 rounded-full" />
      <Skeleton className="h-4 w-32" />
    </div>
    <Skeleton className="h-4 w-16" />
  </div>
);

interface TableSkeletonProps {
  count?: number;
  showHeader?: boolean;
}

export const TableSkeleton: FC<TableSkeletonProps> = ({ count = 5, showHeader = true }) => {
  return (
    <div className="space-y-8 border shadow-sm rounded-md p-4">
      {showHeader && <TableHeaderSkeleton className="" />}
      {Array.from({ length: count }).map((_, i) => (
        <TableRowSkeleton key={i} />
      ))}
    </div>
  );
};

export default TableSkeleton;
