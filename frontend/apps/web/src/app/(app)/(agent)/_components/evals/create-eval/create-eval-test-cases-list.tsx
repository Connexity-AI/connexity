'use client';

import { Minus, Plus, X } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { DifficultyBadge } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-difficulty-badge';

import type { CreateEvalTestCaseValue } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';

interface RunsStepperProps {
  value: number;
  onChange: (next: number) => void;
}

function RunsStepper({ value, onChange }: RunsStepperProps) {
  return (
    <div className="inline-flex items-center gap-1">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        onClick={() => onChange(Math.max(1, value - 1))}
        disabled={value <= 1}
      >
        <Minus className="h-3 w-3" />
      </Button>

      <span className="w-6 text-center font-mono text-xs tabular-nums">{value}</span>

      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        onClick={() => onChange(value + 1)}
      >
        <Plus className="h-3 w-3" />
      </Button>
    </div>
  );
}

interface TagListProps {
  tags: string[];
}

function TagList({ tags }: TagListProps) {
  if (tags.length === 0) return null;

  return (
    <div className="mt-0.5 flex flex-wrap gap-1">
      {tags.slice(0, 3).map((t) => (
        <span key={t} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
          {t}
        </span>
      ))}
    </div>
  );
}

interface RunsCellProps {
  readOnly: boolean;
  value: number;
  onChange: (next: number) => void;
}

function RunsCell({ readOnly, value, onChange }: RunsCellProps) {
  if (readOnly) {
    return <span className="font-mono text-xs tabular-nums text-muted-foreground">{value}</span>;
  }

  return <RunsStepper value={value} onChange={onChange} />;
}

interface RemoveCellProps {
  readOnly: boolean;
  onRemove: () => void;
}

function RemoveCell({ readOnly, onRemove }: RemoveCellProps) {
  if (readOnly) return null;

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="h-6 w-6 text-muted-foreground/30 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
      onClick={onRemove}
    >
      <X className="h-3 w-3" />
    </Button>
  );
}

interface TestCaseRowProps {
  tc: CreateEvalTestCaseValue;
  readOnly: boolean;
  onChangeRepetitions: (next: number) => void;
  onRemove: () => void;
}

function TestCaseRow({ tc, readOnly, onChangeRepetitions, onRemove }: TestCaseRowProps) {
  return (
    <li className="group grid grid-cols-[1fr_90px_90px_32px] items-center gap-2 border-b border-border/40 py-2 last:border-b-0 hover:bg-accent/20">
      <div className="min-w-0">
        <p className="truncate text-sm">{tc.name}</p>
        <TagList tags={tc.tags} />
      </div>

      <div>
        <DifficultyBadge difficulty={tc.difficulty} />
      </div>

      <div>
        <RunsCell readOnly={readOnly} value={tc.repetitions} onChange={onChangeRepetitions} />
      </div>

      <div>
        <RemoveCell readOnly={readOnly} onRemove={onRemove} />
      </div>
    </li>
  );
}

interface TestCasesListProps {
  fieldIds: string[];
  cases: CreateEvalTestCaseValue[];
  readOnly: boolean;
  onUpdate: (index: number, value: CreateEvalTestCaseValue) => void;
  onRemove: (index: number) => void;
}

export function TestCasesList({
  fieldIds,
  cases,
  readOnly,
  onUpdate,
  onRemove,
}: TestCasesListProps) {
  return (
    <div>
      <div className="grid grid-cols-[1fr_90px_90px_32px] items-center gap-2 border-b border-border pb-2 text-[10px] uppercase tracking-wider text-muted-foreground/60">
        <span>Name</span>
        <span>Difficulty</span>
        <span>Runs</span>
        <span />
      </div>

      <ul>
        {fieldIds.map((fieldId, index) => {
          const tc = cases[index];
          if (!tc) return null;
          return (
            <TestCaseRow
              key={fieldId}
              tc={tc}
              readOnly={readOnly}
              onChangeRepetitions={(next) => onUpdate(index, { ...tc, repetitions: next })}
              onRemove={() => onRemove(index)}
            />
          );
        })}
      </ul>
    </div>
  );
}
