'use client';

import { useFormContext } from 'react-hook-form';

import { Input } from '@workspace/ui/components/ui/input';
import { Textarea } from '@workspace/ui/components/ui/textarea';

import { Field, SectionHeading } from '@/app/(app)/(agent)/_components/tools/tool-editor-field';
import { ToolEditorHeader } from '@/app/(app)/(agent)/_components/tools/tool-editor-header';

import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

const DEFAULT_TOOLS_WITH_URL = new Set(['transfer_call']);

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
  const { register } = useFormContext<AgentFormValues>();
  const showUrl = DEFAULT_TOOLS_WITH_URL.has(toolName);

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

          {showUrl && (
            <div>
              <SectionHeading>Endpoint</SectionHeading>
              <Field
                label="URL"
                hint="Webhook called when the model invokes this tool."
              >
                <Input
                  {...register(`tools.${toolIndex}.url`)}
                  placeholder="https://api.example.com/transfer"
                  className="h-9 text-sm font-mono w-full"
                />
              </Field>
            </div>
          )}
        </fieldset>
      </div>
    </div>
  );
}
