'use client';

import { Tag } from 'lucide-react';

import { Toggle } from '@workspace/ui/components/ui/toggle';
import { ToggleGroup, ToggleGroupItem } from '@workspace/ui/components/ui/toggle-group';

import {
  testCasesDifficultyValues,
  testCasesStatusValues,
} from '@/common/url-generator/parsers';

type StatusFilter = (typeof testCasesStatusValues)[number];
type DifficultyFilter = (typeof testCasesDifficultyValues)[number];

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
];

const DIFFICULTY_OPTIONS: { value: DifficultyFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'normal', label: 'Normal' },
  { value: 'hard', label: 'Hard' },
];

const pillItemClass =
  'h-auto min-w-0 cursor-pointer rounded px-2.5 py-1 text-xs text-muted-foreground transition-colors data-[state=on]:bg-foreground data-[state=on]:text-background hover:bg-accent hover:text-foreground';

interface TestCasesFilterBarProps {
  statusFilter: StatusFilter;
  difficultyFilter: DifficultyFilter;
  onStatusChange: (value: StatusFilter) => void;
  onDifficultyChange: (value: DifficultyFilter) => void;
  groupByTags: boolean;
  onToggleGroupByTags: () => void;
}

export function TestCasesFilterBar({
  statusFilter,
  difficultyFilter,
  onStatusChange,
  onDifficultyChange,
  groupByTags,
  onToggleGroupByTags,
}: TestCasesFilterBarProps) {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border px-4 py-2">
      <ToggleGroup
        type="single"
        value={statusFilter}
        onValueChange={(value) => {
          if (value) onStatusChange(value as StatusFilter);
        }}
        className="shrink-0 gap-0.5 rounded-md bg-accent/40 p-0.5"
      >
        {STATUS_OPTIONS.map((option) => (
          <ToggleGroupItem key={option.value} value={option.value} className={pillItemClass}>
            {option.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>

      <div className="h-4 w-px shrink-0 bg-border" />

      <ToggleGroup
        type="single"
        value={difficultyFilter}
        onValueChange={(value) => {
          if (value) onDifficultyChange(value as DifficultyFilter);
        }}
        className="shrink-0 gap-0.5 rounded-md bg-accent/40 p-0.5"
      >
        {DIFFICULTY_OPTIONS.map((option) => (
          <ToggleGroupItem key={option.value} value={option.value} className={pillItemClass}>
            {option.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>

      <div className="h-4 w-px shrink-0 bg-border" />

      <Toggle
        variant="outline"
        pressed={groupByTags}
        onPressedChange={onToggleGroupByTags}
        className="h-7 min-w-0 cursor-pointer gap-1.5 rounded border-border px-2.5 text-xs text-muted-foreground data-[state=on]:border-foreground data-[state=on]:bg-foreground data-[state=on]:text-background hover:bg-accent/50 hover:text-foreground"
      >
        <Tag className="h-3 w-3" />
        Group by tags
      </Toggle>
    </div>
  );
}
