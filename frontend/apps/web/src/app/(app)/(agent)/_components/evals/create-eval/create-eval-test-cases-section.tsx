'use client';
'use no memo';

import { useMemo, useState } from 'react';

import { Search } from 'lucide-react';
import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import { FormMessage } from '@workspace/ui/components/ui/form';
import { Input } from '@workspace/ui/components/ui/input';

import { useCreateEvalReadOnly } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import { Section } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-section-primitives';
import { TestCasesEmpty } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-empty';
import { TestCasesHeaderActions } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-header-actions';
import { TestCasesList } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-list';
import { TestCasesPickerList } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-picker-list';
import { useTestCases } from '@/app/(app)/(agent)/_hooks/use-test-cases';

import type {
  CreateEvalFormValues,
  CreateEvalTestCaseValue,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { TestCasePublic } from '@/client/types.gen';

function plural(count: number, singular: string, pluralForm: string = singular + 's') {
  if (count === 1) return singular;
  return pluralForm;
}

function toPickerRow(tc: TestCasePublic): CreateEvalTestCaseValue {
  return {
    test_case_id: tc.id,
    name: tc.name,
    difficulty: tc.difficulty ?? null,
    tags: tc.tags ?? [],
    repetitions: 1,
  };
}

interface AddTestCasesDialogProps {
  agentId: string;
  excludeIds: Set<string>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (items: CreateEvalTestCaseValue[]) => void;
}

function AddTestCasesDialog({
  agentId,
  excludeIds,
  open,
  onOpenChange,
  onAdd,
}: AddTestCasesDialogProps) {
  const { data, isLoading } = useTestCases(agentId);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const available = useMemo(() => {
    const all = data?.data ?? [];
    const q = query.trim().toLowerCase();
    return all
      .filter((tc) => !excludeIds.has(tc.id))
      .filter((tc) => q === '' || tc.name.toLowerCase().includes(q));
  }, [data, excludeIds, query]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setQuery('');
      setSelected(new Set());
    }
    onOpenChange(next);
  };

  const handleAdd = () => {
    const toAdd = available.filter((tc) => selected.has(tc.id)).map(toPickerRow);
    if (toAdd.length === 0) return;
    onAdd(toAdd);
    handleOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="flex max-h-[70vh] flex-col gap-0 p-0 sm:max-w-lg">
        <DialogHeader className="border-b border-border px-5 py-3">
          <DialogTitle className="text-sm font-medium">Add test cases</DialogTitle>
        </DialogHeader>

        <div className="flex items-center gap-2 border-b border-border px-5 py-2.5">
          <Search size={20} className=" text-muted-foreground/60" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search test cases…"
            className="h-8"
          />
        </div>

        <div className="min-h-0 flex-1 overflow-auto">
          <TestCasesPickerList
            isLoading={isLoading}
            available={available}
            selected={selected}
            onToggle={toggle}
          />
        </div>

        <DialogFooter className="flex shrink-0 items-center justify-between border-t border-border px-5 py-3">
          <span className="text-xs text-muted-foreground">{selected.size} selected</span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 text-xs"
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              className="h-8 text-xs"
              onClick={handleAdd}
              disabled={selected.size === 0}
            >
              Add {selected.size} test {plural(selected.size, 'case')}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface TestCasesBodyProps {
  cases: CreateEvalTestCaseValue[];
  fieldIds: string[];
  readOnly: boolean;
  onOpenPicker: () => void;
  onUpdate: (index: number, value: CreateEvalTestCaseValue) => void;
  onRemove: (index: number) => void;
}

function TestCasesBody({
  cases,
  fieldIds,
  readOnly,
  onOpenPicker,
  onUpdate,
  onRemove,
}: TestCasesBodyProps) {
  if (cases.length === 0) {
    return <TestCasesEmpty readOnly={readOnly} onOpenPicker={onOpenPicker} />;
  }

  return (
    <TestCasesList
      fieldIds={fieldIds}
      cases={cases}
      readOnly={readOnly}
      onUpdate={onUpdate}
      onRemove={onRemove}
    />
  );
}

function ErrorMessage({ message }: { message: string | undefined }) {
  if (typeof message !== 'string') return null;
  return <FormMessage className="mt-2">{message}</FormMessage>;
}

export function TestCasesSection({ agentId }: { agentId: string }) {
  const form = useFormContext<CreateEvalFormValues>();

  const readOnly = useCreateEvalReadOnly();

  const fieldArray = useFieldArray({ control: form.control, name: 'test_cases' });
  const testCases = useWatch({ control: form.control, name: 'test_cases' });

  const [pickerOpen, setPickerOpen] = useState(false);

  const cases = testCases ?? [];
  const totalRuns = cases.reduce((sum, tc) => sum + (tc.repetitions || 0), 0);
  const excludeIds = new Set(cases.map((tc) => tc.test_case_id));

  const headerTitle = `Test Cases · ${cases.length} ${plural(cases.length, 'case')} · ${totalRuns} ${plural(totalRuns, 'run')}`;

  const handleAdd = (items: CreateEvalTestCaseValue[]) => {
    items.forEach((item) => fieldArray.append(item));
  };

  const handleSetAll = (value: number) => {
    fieldArray.replace(cases.map((tc) => ({ ...tc, repetitions: value })));
  };

  const errorMessage = form.formState.errors.test_cases?.message;

  return (
    <Section>
      <Section.Header
        title={headerTitle}
        action={
          <TestCasesHeaderActions
            readOnly={readOnly}
            casesCount={cases.length}
            onOpenPicker={() => setPickerOpen(true)}
            onSetAll={handleSetAll}
          />
        }
      />
      <Section.Body>
        <TestCasesBody
          cases={cases}
          fieldIds={fieldArray.fields.map((field) => field.id)}
          readOnly={readOnly}
          onOpenPicker={() => setPickerOpen(true)}
          onUpdate={(index, value) => fieldArray.update(index, value)}
          onRemove={(index) => fieldArray.remove(index)}
        />
        <ErrorMessage message={typeof errorMessage === 'string' ? errorMessage : undefined} />
      </Section.Body>

      <AddTestCasesDialog
        agentId={agentId}
        excludeIds={excludeIds}
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onAdd={handleAdd}
      />
    </Section>
  );
}
