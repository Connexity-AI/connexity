import { AlertTriangle } from 'lucide-react';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { cn } from '@workspace/ui/lib/utils';

import type { TestCasePublic } from '@/client/types.gen';
import type { ColumnDef } from '@tanstack/react-table';

interface Options {
  selectedIds: Set<string>;
  allSelected: boolean;
  someSelected: boolean;
  onToggleRow: (id: string, checked: boolean) => void;
  onToggleAll: (checked: boolean) => void;
}

export function getTestCasesColumns({
  selectedIds,
  allSelected,
  someSelected,
  onToggleRow,
  onToggleAll,
}: Options): ColumnDef<TestCasePublic>[] {
  return [
    {
      id: 'select',
      header: () => (
        <div onClick={(e) => e.stopPropagation()} className="flex items-center">
          <Checkbox
            aria-label="Select all test cases"
            checked={allSelected ? true : someSelected ? 'indeterminate' : false}
            onCheckedChange={(value) => onToggleAll(value === true)}
          />
        </div>
      ),
      cell: ({ row }) => (
        <div onClick={(e) => e.stopPropagation()} className="flex items-center">
          <Checkbox
            aria-label={`Select ${row.original.name}`}
            checked={selectedIds.has(row.original.id)}
            onCheckedChange={(value) => onToggleRow(row.original.id, value === true)}
          />
        </div>
      ),
      size: 32,
      enableSorting: false,
    },
    {
      accessorKey: 'name',
      header: 'Test Case Name',
      enableSorting: true,
      cell: ({ row }) => (
        <span className="block min-w-30 max-w-85 truncate text-sm text-foreground">
          {row.original.name}
        </span>
      ),
    },
    {
      accessorKey: 'difficulty',
      header: 'Difficulty',
      enableSorting: true,
      cell: ({ row }) => {
        const difficulty = row.original.difficulty ?? 'normal';
        return (
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px]',
              difficulty === 'hard'
                ? 'bg-orange-500/15 text-orange-400'
                : 'bg-accent text-muted-foreground'
            )}
          >
            {difficulty === 'hard' && <AlertTriangle className="h-2.5 w-2.5" />}
            {difficulty === 'hard' ? 'Hard' : 'Normal'}
          </span>
        );
      },
    },
    {
      accessorKey: 'tags',
      header: 'Tags',
      enableSorting: false,
      cell: ({ row }) => {
        const tags = row.original.tags ?? [];
        if (tags.length === 0) {
          return <span className="text-xs text-muted-foreground/50">—</span>;
        }
        return (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <span
                key={tag}
                className="rounded bg-accent px-1.5 py-0.5 text-[10px] text-muted-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        );
      },
    },
  ];
}
