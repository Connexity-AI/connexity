import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@workspace/ui/components/ui/table';
import { Skeleton } from '@workspace/ui/components/ui/skeleton';

import type { FC } from 'react';

interface TableSkeletonProps {
  count?: number;
  columns?: number;
}

export const TableSkeleton: FC<TableSkeletonProps> = ({ count = 5, columns = 2 }) => {
  return (
    <div className="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {Array.from({ length: columns }).map((_, index) => (
              <TableHead key={index}>
                <Skeleton className="h-4 w-20" />
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: count }).map((_, rowIdx) => (
            <TableRow key={rowIdx} className="hover:bg-transparent">
              {Array.from({ length: columns }).map((_, colIdx) => (
                <TableCell key={colIdx}>
                  <Skeleton className="h-4 w-32" />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default TableSkeleton;
