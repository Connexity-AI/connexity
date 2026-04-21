'use client';
'use no memo';

import { flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { ChevronDown } from 'lucide-react';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@workspace/ui/components/ui/table';
import { cn } from '@workspace/ui/lib/utils';

import type { TestCasePublic } from '@/client/types.gen';
import type { ColumnDef } from '@tanstack/react-table';

export interface TestCasesTagGroup {
  tag: string;
  items: TestCasePublic[];
}

interface GroupedTestCasesTableProps {
  columns: ColumnDef<TestCasePublic>[];
  groups: TestCasesTagGroup[];
  collapsedGroups: Set<string>;
  onToggleGroup: (tag: string) => void;
  selectedIds: Set<string>;
  onToggleRow: (id: string, checked: boolean) => void;
  onOpenRow: (item: TestCasePublic) => void;
}

export function GroupedTestCasesTable({
  columns,
  groups,
  collapsedGroups,
  onToggleGroup,
  selectedIds,
  onToggleRow,
  onOpenRow,
}: GroupedTestCasesTableProps) {
  const headerTable = useReactTable({
    data: [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Table>
      <TableHeader>
        {headerTable.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id} className="hover:bg-transparent">
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {header.isPlaceholder
                  ? null
                  : flexRender(header.column.columnDef.header, header.getContext())}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {groups.map((group) => {
          const label = group.tag === '__untagged__' ? 'Untagged' : group.tag;
          return (
            <GroupRows
              key={group.tag}
              tag={group.tag}
              label={label}
              items={group.items}
              isCollapsed={collapsedGroups.has(group.tag)}
              onToggle={() => onToggleGroup(group.tag)}
              selectedIds={selectedIds}
              onToggleRow={onToggleRow}
              onOpenRow={onOpenRow}
              columnCount={columns.length}
            />
          );
        })}
      </TableBody>
    </Table>
  );
}

interface GroupRowsProps {
  tag: string;
  label: string;
  items: TestCasePublic[];
  isCollapsed: boolean;
  onToggle: () => void;
  selectedIds: Set<string>;
  onToggleRow: (id: string, checked: boolean) => void;
  onOpenRow: (item: TestCasePublic) => void;
  columnCount: number;
}

function GroupRows({
  tag,
  label,
  items,
  isCollapsed,
  onToggle,
  selectedIds,
  onToggleRow,
  onOpenRow,
  columnCount,
}: GroupRowsProps) {
  return (
    <>
      <TableRow className="hover:bg-transparent">
        <TableCell
          colSpan={columnCount}
          className="cursor-pointer border-b border-border bg-accent/20 px-5 py-2 hover:bg-accent/40"
          onClick={onToggle}
        >
          <div className="flex items-center gap-2">
            <ChevronDown
              className={cn(
                'h-3 w-3 text-muted-foreground/60 transition-transform duration-150',
                isCollapsed && '-rotate-90'
              )}
            />
            {tag !== '__untagged__' ? (
              <span className="rounded bg-accent px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {label}
              </span>
            ) : (
              <span className="text-[10px] italic text-muted-foreground/50">{label}</span>
            )}
            <span className="ml-auto text-[10px] text-muted-foreground/40">{items.length}</span>
          </div>
        </TableCell>
      </TableRow>
      {!isCollapsed &&
        items.map((item) => (
          <GroupItemRow
            key={`${tag}:${item.id}`}
            item={item}
            checked={selectedIds.has(item.id)}
            onToggle={(checked) => onToggleRow(item.id, checked)}
            onOpen={() => onOpenRow(item)}
          />
        ))}
    </>
  );
}

function GroupItemRow({
  item,
  checked,
  onToggle,
  onOpen,
}: {
  item: TestCasePublic;
  checked: boolean;
  onToggle: (checked: boolean) => void;
  onOpen: () => void;
}) {
  const difficulty = item.difficulty ?? 'normal';
  const tags = item.tags ?? [];

  return (
    <TableRow className={cn('cursor-pointer', checked && 'bg-accent/50')} onClick={onOpen}>
      <TableCell className="align-middle" onClick={(event) => event.stopPropagation()}>
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onToggle(event.target.checked)}
          className="h-3.5 w-3.5 cursor-pointer rounded border-border accent-foreground"
          aria-label={`Select ${item.name}`}
        />
      </TableCell>
      <TableCell className="align-middle">
        <span className="block min-w-30 max-w-85 truncate text-sm text-foreground">
          {item.name}
        </span>
      </TableCell>
      <TableCell className="align-middle">
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px]',
            difficulty === 'hard'
              ? 'bg-orange-500/15 text-orange-400'
              : 'bg-accent text-muted-foreground'
          )}
        >
          {difficulty === 'hard' ? 'Hard' : 'Normal'}
        </span>
      </TableCell>
      <TableCell className="align-middle">
        {tags.length === 0 ? (
          <span className="text-xs text-muted-foreground/50">—</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {tags.map((tagName) => (
              <span
                key={tagName}
                className="rounded bg-accent px-1.5 py-0.5 text-[10px] text-muted-foreground"
              >
                {tagName}
              </span>
            ))}
          </div>
        )}
      </TableCell>
    </TableRow>
  );
}
