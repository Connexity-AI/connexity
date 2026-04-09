'use client';

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { parseAsInteger, useQueryStates } from 'nuqs';

import { Button } from '@workspace/ui/components/ui/button';

import type { UseQueryStatesKeysMap, Values } from 'nuqs';

type PaginationKeysMap = UseQueryStatesKeysMap & {
  page: ReturnType<typeof parseAsInteger.withDefault>;
  pageSize: ReturnType<typeof parseAsInteger.withDefault>;
};

interface TablePaginationProps<T extends PaginationKeysMap> {
  totalCount: number;
  parser: T;
}

export function TablePagination<T extends PaginationKeysMap>({
  totalCount,
  parser,
}: TablePaginationProps<T>) {
  const [params, setParams] = useQueryStates(parser, {
    shallow: false,
  });

  const page = params.page as number;
  const pageSize = params.pageSize as number;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const update = (values: Partial<Values<T>>) => setParams(values);

  return (
    <div className="flex items-center justify-between">
      <div className="flex w-full items-center gap-6 lg:ml-auto lg:w-fit">
        <div className="flex w-fit items-center justify-center text-sm font-medium">
          Page {page} of {totalPages}
        </div>

        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          <Button
            variant="outline"
            className="hidden h-8 w-8 p-0 lg:flex"
            size="icon"
            onClick={() => update({ page: 1 } as Partial<Values<T>>)}
            disabled={page <= 1}
          >
            <span className="sr-only">Go to first page</span>
            <ChevronsLeft className="h-4 w-4" />
          </Button>

          <Button
            variant="outline"
            className="h-8 w-8"
            size="icon"
            onClick={() => update({ page: Math.max(1, page - 1) } as Partial<Values<T>>)}
            disabled={page <= 1}
          >
            <span className="sr-only">Go to previous page</span>
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <Button
            variant="outline"
            className="h-8 w-8"
            size="icon"
            onClick={() =>
              update({
                page: Math.min(totalPages, page + 1),
              } as Partial<Values<T>>)
            }
            disabled={page >= totalPages}
          >
            <span className="sr-only">Go to next page</span>
            <ChevronRight className="h-4 w-4" />
          </Button>

          <Button
            variant="outline"
            className="hidden h-8 w-8 lg:flex"
            size="icon"
            onClick={() => update({ page: totalPages } as Partial<Values<T>>)}
            disabled={page >= totalPages}
          >
            <span className="sr-only">Go to last page</span>
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
