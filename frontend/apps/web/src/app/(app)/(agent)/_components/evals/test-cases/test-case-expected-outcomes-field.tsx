'use client';
'use no memo';

import { Plus, X } from 'lucide-react';
import { Controller, useFieldArray, useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import { Textarea } from '@workspace/ui/components/ui/textarea';

import { FieldLabel } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';

import type { TestCaseFormValues } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';

interface OutcomeRowProps {
  index: number;
  onRemove: (index: number) => void;
}

function OutcomeRow({ index, onRemove }: OutcomeRowProps) {
  const form = useFormContext<TestCaseFormValues>();
  return (
    <div className="group relative">
      <div className="flex items-start gap-2">
        <span className="mt-2 w-4 shrink-0 font-mono text-[10px] text-muted-foreground/50">
          {index + 1}.
        </span>

        <Controller
          control={form.control}
          name={`expected_outcomes.${index}.value`}
          render={({ field }) => (
            <Textarea
              {...field}
              placeholder="Expected outcome statement…"
              className="min-h-15 flex-1 resize-none text-sm leading-relaxed"
            />
          )}
        />
      </div>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => onRemove(index)}
        title="Remove outcome"
        className="absolute right-1 top-1 h-auto w-auto rounded bg-background p-1 text-muted-foreground/30 opacity-0 transition-colors hover:bg-background hover:text-red-400 group-hover:opacity-100 [&_svg]:size-3.5"
      >
        <X />
      </Button>
    </div>
  );
}

interface OutcomesListProps {
  fields: { id: string }[];
  onRemove: (index: number) => void;
}

function OutcomesList({ fields, onRemove }: OutcomesListProps) {
  if (fields.length === 0) {
    return <p className="text-xs italic text-muted-foreground/50">No expected outcomes</p>;
  }
  return (
    <div className="space-y-2.5">
      {fields.map((field, index) => (
        <OutcomeRow key={field.id} index={index} onRemove={onRemove} />
      ))}
    </div>
  );
}

export function TestCaseExpectedOutcomesField() {
  const form = useFormContext<TestCaseFormValues>();
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'expected_outcomes',
  });

  const handleAdd = () => append({ value: '' });

  return (
    <div>
      <FieldLabel>Expected outcomes</FieldLabel>

      <OutcomesList fields={fields} onRemove={remove} />

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={handleAdd}
        className="mt-2 h-auto gap-1 px-0 py-0 text-xs font-normal text-muted-foreground/50 hover:bg-transparent hover:text-muted-foreground [&_svg]:size-3"
      >
        <Plus />
        Add expected outcome
      </Button>
    </div>
  );
}
