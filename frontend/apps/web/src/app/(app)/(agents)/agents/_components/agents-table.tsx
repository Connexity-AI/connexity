'use client';

import { agentsParser } from '@/common/url-generator/parsers';
import { Bot } from 'lucide-react';
import { useQueryStates } from 'nuqs';

import { TableSkeleton } from '@workspace/ui/components/skeletons/table';
import { cn } from '@workspace/ui/lib/utils';

import { useAgents } from '@/app/(app)/(agents)/_hooks/use-agents';
import { getAgentsColumns } from '@/app/(app)/(agents)/agents/_components/get-agents-columns';
import { DataTable } from '@/components/common/data-table/data-table';
import { TablePagination } from '@/components/common/data-table/table-pagination';

export function AgentsTable() {
  const [params] = useQueryStates(agentsParser, {
    shallow: false,
  });

  const filters = {
    name: params.name || undefined,
    page: params.page,
    pageSize: params.pageSize,
  };

  const { data, isLoading, isFetching } = useAgents(filters);
  const columns = getAgentsColumns();

  if (isLoading) {
    return (
      <div className="p-6">
        <TableSkeleton />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col min-w-0">
      {/* Table */}
      <div
        className={cn(
          'flex-1 overflow-auto p-6 transition-opacity duration-200',
          isFetching && 'pointer-events-none opacity-50'
        )}
      >
        <DataTable
          columns={columns}
          data={data?.rows ?? []}
          initialSortingState={[{ id: 'updated_at', desc: true }]}
          footer={<TablePagination totalCount={data?.totalCount ?? 0} parser={agentsParser} />}
          emptyState={
            <div className="flex flex-col items-center justify-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <Bot className="h-5 w-5 text-muted-foreground/50" />
              </div>
              <p className="text-sm">No agents found</p>
            </div>
          }
        />
      </div>
    </div>
  );
}
