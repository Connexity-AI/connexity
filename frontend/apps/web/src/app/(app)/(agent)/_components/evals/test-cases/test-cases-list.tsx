'use client';

import { AlertTriangle, ChevronDown } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { cn } from '@workspace/ui/lib/utils';

import type { TestCasesTagGroup } from './use-test-cases-grouping';
import type { TestCasePublic } from '@/client/types.gen';

const ROW_GRID = 'grid grid-cols-[32px_minmax(0,1fr)_120px_minmax(0,1fr)] items-center gap-4';

interface TestCasesListProps {
  groupByTags: boolean;
  filtered: TestCasePublic[];
  tagGroups: TestCasesTagGroup[];
  collapsedGroups: Set<string>;
  selectedIds: Set<string>;
  onToggleGroup: (tag: string) => void;
  onToggleRow: (id: string, checked: boolean) => void;
  onOpenRow: (testCase: TestCasePublic) => void;
  onClearFilters: () => void;
}

export function TestCasesList({
  groupByTags,
  filtered,
  tagGroups,
  collapsedGroups,
  selectedIds,
  onToggleGroup,
  onToggleRow,
  onOpenRow,
  onClearFilters,
}: TestCasesListProps) {
  if (filtered.length === 0) {
    return <EmptyState onClearFilters={onClearFilters} />;
  }

  if (groupByTags) {
    return (
      <ul>
        {tagGroups.map((group) => {
          const label = group.tag === '__untagged__' ? 'Untagged' : group.tag;
          const isCollapsed = collapsedGroups.has(group.tag);
          return (
            <li key={group.tag}>
              <GroupHeader
                label={label}
                count={group.items.length}
                isCollapsed={isCollapsed}
                isUntagged={group.tag === '__untagged__'}
                onToggle={() => onToggleGroup(group.tag)}
              />
              {!isCollapsed && (
                <ul>
                  {group.items.map((testCase) => (
                    <TestCaseRow
                      key={`${group.tag}:${testCase.id}`}
                      testCase={testCase}
                      selected={selectedIds.has(testCase.id)}
                      onToggle={(checked) => onToggleRow(testCase.id, checked)}
                      onOpen={() => onOpenRow(testCase)}
                    />
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    );
  }

  return (
    <ul>
      {filtered.map((testCase) => (
        <TestCaseRow
          key={testCase.id}
          testCase={testCase}
          selected={selectedIds.has(testCase.id)}
          onToggle={(checked) => onToggleRow(testCase.id, checked)}
          onOpen={() => onOpenRow(testCase)}
        />
      ))}
    </ul>
  );
}

interface GroupHeaderProps {
  label: string;
  count: number;
  isCollapsed: boolean;
  isUntagged: boolean;
  onToggle: () => void;
}

function GroupHeader({ label, count, isCollapsed, isUntagged, onToggle }: GroupHeaderProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="sticky top-0 z-5 flex w-full items-center gap-2 border-b border-border bg-background/95 px-5 py-1.5 text-left text-[10px] uppercase tracking-wider text-muted-foreground/70 backdrop-blur hover:bg-accent/40"
    >
      <ChevronDown
        className={cn(
          'h-3 w-3 text-muted-foreground/60 transition-transform duration-150',
          isCollapsed && '-rotate-90'
        )}
      />
      {isUntagged ? (
        <span className="italic text-muted-foreground/50">{label}</span>
      ) : (
        <span className="rounded bg-accent px-1.5 py-0.5 text-[10px] normal-case tracking-normal text-muted-foreground">
          {label}
        </span>
      )}
      <span className="ml-auto text-muted-foreground/50">{count}</span>
    </button>
  );
}

interface TestCaseRowProps {
  testCase: TestCasePublic;
  selected: boolean;
  onToggle: (checked: boolean) => void;
  onOpen: () => void;
}

function TestCaseRow({ testCase, selected, onToggle, onOpen }: TestCaseRowProps) {
  const difficulty = testCase.difficulty ?? 'normal';
  const tags = testCase.tags ?? [];

  return (
    <li
      className={cn(
        ROW_GRID,
        'group cursor-pointer select-none border-b border-border/40 px-5 py-2.5 transition-colors',
        selected ? 'bg-accent/50' : 'hover:bg-accent/20'
      )}
      onClick={onOpen}
    >
      <div className="flex items-center justify-start" onClick={(e) => e.stopPropagation()}>
        <Checkbox
          aria-label={`Select ${testCase.name}`}
          checked={selected}
          onCheckedChange={(value) => onToggle(value === true)}
        />
      </div>
      <span className="min-w-0 truncate text-sm text-foreground">{testCase.name}</span>
      <div>
        <span
          className={cn(
            'inline-flex w-fit items-center gap-1 rounded px-1.5 py-0.5 text-[10px]',
            difficulty === 'hard'
              ? 'bg-orange-500/15 text-orange-400'
              : 'bg-accent text-muted-foreground'
          )}
        >
          {difficulty === 'hard' && <AlertTriangle className="h-2.5 w-2.5" />}
          {difficulty === 'hard' ? 'Hard' : 'Normal'}
        </span>
      </div>
      {tags.length === 0 ? (
        <span className="text-xs text-muted-foreground/50">—</span>
      ) : (
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
      )}
    </li>
  );
}

function EmptyState({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16">
      <p className="text-sm text-muted-foreground">No test cases match the current filters</p>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClearFilters}
        className="h-7 px-2 text-xs text-muted-foreground/50 hover:bg-transparent hover:text-muted-foreground"
      >
        Clear all filters
      </Button>
    </div>
  );
}
