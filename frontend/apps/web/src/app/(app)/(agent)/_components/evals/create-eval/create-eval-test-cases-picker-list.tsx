'use client';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { cn } from '@workspace/ui/lib/utils';

import { DifficultyBadge } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-difficulty-badge';

import type { TestCasePublic } from '@/client/types.gen';

interface TestCasesPickerListProps {
  isLoading: boolean;
  available: TestCasePublic[];
  selected: Set<string>;
  onToggle: (id: string) => void;
}

export function TestCasesPickerList({
  isLoading,
  available,
  selected,
  onToggle,
}: TestCasesPickerListProps) {
  if (isLoading) {
    return <p className="px-5 py-6 text-center text-xs text-muted-foreground/60">Loading…</p>;
  }

  if (available.length === 0) {
    return (
      <p className="px-5 py-6 text-center text-xs text-muted-foreground/60">
        No test cases available
      </p>
    );
  }

  return (
    <ul>
      {available.map((tc) => {
        const isChecked = selected.has(tc.id);
        return (
          <li key={tc.id}>
            <div
              role="button"
              tabIndex={0}
              onClick={() => onToggle(tc.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onToggle(tc.id);
                }
              }}
              className={cn(
                'flex w-full cursor-pointer items-center gap-3 px-5 py-2 text-left hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isChecked && 'bg-accent/40'
              )}
            >
              <Checkbox checked={isChecked} tabIndex={-1} />

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{tc.name}</p>

                <div className="mt-0.5 flex items-center gap-1.5">
                  <DifficultyBadge difficulty={tc.difficulty} />
                  {(tc.tags ?? []).slice(0, 3).map((t) => (
                    <span
                      key={t}
                      className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
