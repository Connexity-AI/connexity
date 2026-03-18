import { Skeleton } from '@workspace/ui/components/ui/skeleton';

import type { FC } from 'react';

const CardSmallSkeleton: FC = () => {
  return (
    <div className="rounded-xl border border-gray-200 p-4 shadow-sm dark:border-gray-800">
      <div className="flex items-start justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4 rounded-full" />
      </div>

      <div className="mt-4">
        <Skeleton className="h-6 w-40" />
      </div>

      <div className="mt-4">
        <Skeleton className="h-4 w-28" />
      </div>
    </div>
  );
};

export default CardSmallSkeleton;
