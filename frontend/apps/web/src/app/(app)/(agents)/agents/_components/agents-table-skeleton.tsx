'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@workspace/ui/components/ui/table';
import { Skeleton } from '@workspace/ui/components/ui/skeleton';

import { TablePaginationSkeleton } from '@/components/common/data-table/table-pagination-skeleton';

const ROW_HEIGHT = '59px';

interface AgentsTableSkeletonProps {
  rows?: number;
}

export function AgentsTableSkeleton({ rows = 8 }: AgentsTableSkeletonProps) {
  return (
    <div className="flex flex-1 flex-col min-w-0">
      <div className="flex-1 overflow-auto p-6">
        <div className="overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="h-auto px-5 py-2 text-[10px] font-normal uppercase tracking-wider text-muted-foreground/60">
                  <Skeleton className="h-2 w-12" />
                </TableHead>
                <TableHead className="h-auto px-5 py-2 text-[10px] font-normal uppercase tracking-wider text-muted-foreground/60">
                  <Skeleton className="h-2 w-14" />
                </TableHead>
                <TableHead className="h-auto px-5 py-2 text-[10px] font-normal uppercase tracking-wider text-muted-foreground/60">
                  <Skeleton className="h-2 w-14" />
                </TableHead>
                <TableHead className="h-auto px-5 py-2 text-[10px] font-normal uppercase tracking-wider text-muted-foreground/60">
                  <Skeleton className="h-2 w-16" />
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Array.from({ length: rows }).map((_, index) => (
                <TableRow
                  key={index}
                  className="border-border/40 hover:bg-transparent"
                  style={{ height: ROW_HEIGHT }}
                >
                  <TableCell className="px-5 py-2.5">
                    <div className="flex flex-col gap-1">
                      <Skeleton className="h-3.5 w-40" />
                      <Skeleton className="h-3 w-28" />
                    </div>
                  </TableCell>
                  <TableCell className="px-5 py-2.5">
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </TableCell>
                  <TableCell className="px-5 py-2.5">
                    <Skeleton className="h-3.5 w-24" />
                  </TableCell>
                  <TableCell className="px-5 py-2.5">
                    <Skeleton className="h-3.5 w-20" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="border-t border-border px-4 py-3">
            <TablePaginationSkeleton />
          </div>
        </div>
      </div>
    </div>
  );
}
