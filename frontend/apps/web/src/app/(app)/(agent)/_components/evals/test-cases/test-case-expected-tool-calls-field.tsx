'use client';
'use no memo';

import { useMemo } from 'react';

import { Plus, X } from 'lucide-react';
import { Controller, useFieldArray, useFormContext } from 'react-hook-form';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { cn } from '@workspace/ui/lib/utils';

import { FieldLabel } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-drawer-primitives';

import type { TestCaseFormValues } from '@/app/(app)/(agent)/_components/evals/test-cases/test-case-form-schema';
import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

type AgentTool = AgentFormValues['tools'][number];

function ToolOptions({ availableTools }: { availableTools: AgentTool[] }) {
  if (availableTools.length === 0) {
    return (
      <SelectItem value="__none__" disabled>
        No tools defined on this agent
      </SelectItem>
    );
  }
  return (
    <>
      {availableTools.map((tool) => (
        <SelectItem key={tool.id} value={tool.name} className="font-mono text-xs">
          {tool.name || '(unnamed tool)'}
        </SelectItem>
      ))}
    </>
  );
}

interface ToolCallParamsProps {
  index: number;
  tool: AgentTool;
}

function ToolCallParams({ index, tool }: ToolCallParamsProps) {
  const form = useFormContext<TestCaseFormValues>();
  if (tool.parameters.length === 0) return null;

  const paramErrors = (
    form.formState.errors.expected_tool_calls as
      | Record<number, { expected_params?: Record<string, { message?: string } | undefined> }>
      | undefined
  )?.[index]?.expected_params;

  return (
    <Controller
      control={form.control}
      name={`expected_tool_calls.${index}.expected_params`}
      render={({ field }) => {
        const params = (field.value as Record<string, unknown> | null) ?? {};
        return (
          <div className="space-y-2 border-t border-border/50 pt-2">
            <label className="block text-[10px] text-muted-foreground/60">Parameters</label>
            {tool.parameters.map((param) => {
              const errorMessage = paramErrors?.[param.name]?.message;
              return (
                <div key={param.id}>
                  <label className="mb-1 block text-[10px] text-muted-foreground/60">
                    {param.name}
                    <span className="ml-0.5 text-red-400">*</span>
                    {param.description && (
                      <span className="ml-1 text-muted-foreground/40">— {param.description}</span>
                    )}
                  </label>
                  <Input
                    value={params[param.name]?.toString() ?? ''}
                    onChange={(event) =>
                      field.onChange({ ...params, [param.name]: event.target.value })
                    }
                    placeholder={`Enter ${param.name}...`}
                    aria-required="true"
                    aria-invalid={errorMessage ? 'true' : undefined}
                    className={cn(
                      'h-7 font-mono text-xs',
                      errorMessage && 'border-red-400 focus-visible:ring-red-400'
                    )}
                  />
                  {errorMessage && (
                    <p className="mt-1 text-[10px] text-red-400">{errorMessage}</p>
                  )}
                </div>
              );
            })}
          </div>
        );
      }}
    />
  );
}

interface ToolCallCardProps {
  index: number;
  availableTools: AgentTool[];
  toolByName: Map<string, AgentTool>;
  onRemove: (index: number) => void;
}

function ToolCallCard({ index, availableTools, toolByName, onRemove }: ToolCallCardProps) {
  const form = useFormContext<TestCaseFormValues>();
  const toolName = form.watch(`expected_tool_calls.${index}.tool`);
  const selectedTool = toolByName.get(toolName);

  return (
    <div className="group relative rounded-lg border border-border bg-accent/10 p-3">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => onRemove(index)}
        title="Remove tool call"
        className="absolute right-2 top-2 h-auto w-auto rounded bg-background p-1 text-muted-foreground/30 opacity-0 transition-colors hover:bg-background hover:text-red-400 group-hover:opacity-100 [&_svg]:size-3.5"
      >
        <X />
      </Button>
      <div className="space-y-2">
        <div>
          <label className="mb-1 block text-[10px] text-muted-foreground/60">Tool Name</label>

          <Controller
            control={form.control}
            name={`expected_tool_calls.${index}.tool`}
            render={({ field }) => (
              <Select
                value={field.value}
                onValueChange={(value) => {
                  field.onChange(value);
                  form.setValue(`expected_tool_calls.${index}.expected_params`, {});
                }}
              >
                <SelectTrigger className="h-7 font-mono text-xs">
                  <SelectValue placeholder="Select a tool..." />
                </SelectTrigger>

                <SelectContent>
                  <ToolOptions availableTools={availableTools} />
                </SelectContent>
              </Select>
            )}
          />
        </div>
        {selectedTool && <ToolCallParams index={index} tool={selectedTool} />}
      </div>
    </div>
  );
}

interface ToolCallsListProps {
  fields: { id: string }[];
  availableTools: AgentTool[];
  toolByName: Map<string, AgentTool>;
  onRemove: (index: number) => void;
}

function ToolCallsList({ fields, availableTools, toolByName, onRemove }: ToolCallsListProps) {
  if (fields.length === 0) {
    return <p className="text-xs italic text-muted-foreground/50">None</p>;
  }
  return (
    <div className="space-y-3">
      {fields.map((field, index) => (
        <ToolCallCard
          key={field.id}
          index={index}
          availableTools={availableTools}
          toolByName={toolByName}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
}

export function TestCaseExpectedToolCallsField({
  availableTools,
}: {
  availableTools: AgentTool[];
}) {
  const form = useFormContext<TestCaseFormValues>();

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'expected_tool_calls',
  });

  const toolByName = useMemo(
    () => new Map(availableTools.map((tool) => [tool.name, tool])),
    [availableTools]
  );

  const handleAdd = () => append({ tool: '', expected_params: null });

  return (
    <div>
      <FieldLabel>Expected tool calls</FieldLabel>

      <ToolCallsList
        fields={fields}
        availableTools={availableTools}
        toolByName={toolByName}
        onRemove={remove}
      />

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={handleAdd}
        className="mt-2 h-auto gap-1 px-0 py-0 text-xs font-normal text-muted-foreground/50 hover:bg-transparent hover:text-muted-foreground [&_svg]:size-3"
      >
        <Plus />
        Add tool call
      </Button>
    </div>
  );
}
