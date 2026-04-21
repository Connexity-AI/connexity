'use client';

import { ChevronDown, Layers } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@workspace/ui/components/ui/dropdown-menu';
import { cn } from '@workspace/ui/lib/utils';

interface EvalRunsFilterBarProps {
  versions: number[];
  latestVersion: number | null;
  versionFilter: number | null;
  onVersionFilterChange: (value: number | null) => void;
  groupByConfig: boolean;
  onGroupByConfigChange: (value: boolean) => void;
}

export function EvalRunsFilterBar({
  versions,
  latestVersion,
  versionFilter,
  onVersionFilterChange,
  groupByConfig,
  onGroupByConfigChange,
}: EvalRunsFilterBarProps) {
  return (
    <div className="flex h-10 shrink-0 items-center gap-2 border-b border-border px-4 py-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            {versionFilter === null
              ? 'All versions'
              : `v${versionFilter}${versionFilter === latestVersion ? ' (latest)' : ''}`}
            <ChevronDown className="h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="min-w-[160px]">
          <DropdownMenuCheckboxItem
            checked={versionFilter === null}
            onCheckedChange={() => onVersionFilterChange(null)}
          >
            All versions
          </DropdownMenuCheckboxItem>
          <DropdownMenuSeparator />
          {versions.map((v) => (
            <DropdownMenuCheckboxItem
              key={v}
              checked={versionFilter === v}
              onCheckedChange={() => onVersionFilterChange(v)}
            >
              <span>v{v}</span>
              {v === latestVersion ? (
                <span className="ml-auto rounded-full border border-green-500/25 bg-green-500/15 px-1.5 py-0.5 text-[10px] text-green-400">
                  latest
                </span>
              ) : null}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <Button
        variant="ghost"
        size="sm"
        aria-pressed={groupByConfig}
        onClick={() => onGroupByConfigChange(!groupByConfig)}
        className={cn(
          'h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground',
          groupByConfig && 'bg-accent/60 text-foreground'
        )}
      >
        <Layers className="h-3 w-3" />
        Group by config
      </Button>
    </div>
  );
}
