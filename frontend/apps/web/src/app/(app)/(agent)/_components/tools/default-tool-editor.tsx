'use client';

import { useFormContext, useWatch } from 'react-hook-form';

import { Input } from '@workspace/ui/components/ui/input';
import { Textarea } from '@workspace/ui/components/ui/textarea';

import { Field, SectionHeading } from '@/app/(app)/(agent)/_components/tools/tool-editor-field';
import { ToolEditorHeader } from '@/app/(app)/(agent)/_components/tools/tool-editor-header';
import { ToolParameters } from '@/app/(app)/(agent)/_components/tools/tool-parameters';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

interface DefaultToolEditorProps {
  toolIndex: number;
  toolName: string;
  onBack: () => void;
  onDelete: () => void;
  readOnly?: boolean;
}

export function DefaultToolEditor({
  toolIndex,
  toolName,
  onBack,
  onDelete,
  readOnly,
}: DefaultToolEditorProps) {
  const { register, control } = useFormContext<AgentFormValues>();
  const parameters = useWatch({ control, name: `tools.${toolIndex}.parameters` });
  const hasParameters = (parameters?.length ?? 0) > 0;

  return (
    <div className="flex flex-col h-full w-full bg-background">
      <ToolEditorHeader
        toolName={toolName}
        isNew={false}
        onBack={onBack}
        onDelete={onDelete}
        readOnly={readOnly}
      />

      <div className="flex-1 overflow-auto">
        <fieldset disabled={readOnly} className="px-8 py-6 space-y-8">
          <div>
            <SectionHeading>Identity</SectionHeading>
            <div className="space-y-4">
              <Field
                label="Tool name"
                hint="snake_case — the model uses this name to reference the tool"
              >
                <Input
                  {...register(`tools.${toolIndex}.name`)}
                  placeholder="e.g. end_call"
                  className="h-9 text-sm font-mono"
                />
              </Field>
              <Field
                label="Description"
                hint="The model reads this to decide when to invoke the tool. Be specific about the trigger condition."
              >
                <Textarea
                  {...register(`tools.${toolIndex}.description`)}
                  placeholder="Describe what this tool does and when the model should call it..."
                  className="resize-none text-sm h-24"
                />
              </Field>
            </div>
          </div>

          {hasParameters && (
            <div>
              <SectionHeading>Parameters</SectionHeading>
              <p className="text-xs text-muted-foreground/50 mb-4 leading-relaxed">
                Arguments the model collects and passes when invoking this tool.
              </p>
              <ToolParameters toolIndex={toolIndex} />
            </div>
          )}
        </fieldset>
      </div>
    </div>
  );
}
