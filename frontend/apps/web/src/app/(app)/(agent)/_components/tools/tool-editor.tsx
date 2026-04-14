'use client';

import { Plus } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import { cn } from '@workspace/ui/lib/utils';

import { AuthHeaderRow } from '@/app/(app)/(agent)/_components/tools/auth-header-row';
import { Field, SectionHeading } from '@/app/(app)/(agent)/_components/tools/tool-editor-field';
import { ToolEditorHeader } from '@/app/(app)/(agent)/_components/tools/tool-editor-header';
import { ToolParameters } from '@/app/(app)/(agent)/_components/tools/tool-parameters';
import { useToolEditor } from '@/app/(app)/(agent)/_hooks/use-tool-editor';

import type { HttpMethod } from '@/app/(app)/(agent)/_schemas/agent-form';

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

const METHOD_COLOR: Record<HttpMethod, string> = {
  GET: 'text-green-400',
  POST: 'text-blue-400',
  PUT: 'text-amber-400',
  PATCH: 'text-purple-400',
  DELETE: 'text-red-400',
};

interface ToolEditorProps {
  toolIndex: number;
  isNew: boolean;
  onBack: () => void;
  onDelete: () => void;
  readOnly?: boolean;
}

export function ToolEditor({ toolIndex, isNew, onBack, onDelete, readOnly }: ToolEditorProps) {
  const {
    register,
    toolName,
    method,
    authFields,
    setMethod,
    setToolName,
    removeAuth,
    addAuthHeader,
  } = useToolEditor(toolIndex);

  return (
    <div className="flex flex-col h-full w-full bg-background">
      <ToolEditorHeader
        toolName={toolName}
        isNew={isNew}
        onBack={onBack}
        onDelete={onDelete}
        readOnly={readOnly}
      />

      <div className="flex-1 overflow-auto">
        <fieldset disabled={readOnly} className="px-8 py-6 space-y-8">
          {/* Identity */}
          <div>
            <SectionHeading>Identity</SectionHeading>
            <div className="space-y-4">
              <Field
                label="Tool name"
                hint="snake_case — the model uses this name to reference the tool"
              >
                <Input
                  {...register(`tools.${toolIndex}.name`, {
                    onChange: (event) => {
                      const cleaned = event.target.value.replace(/\s/g, '_').toLowerCase();
                      setToolName(cleaned);
                    },
                  })}
                  placeholder="e.g. get_available_time"
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

          {/* Endpoint */}
          <div>
            <SectionHeading>Endpoint</SectionHeading>
            <div className="space-y-4">
              <div className="flex gap-3">
                <Field label="Method">
                  <Select value={method} onValueChange={(value) => setMethod(value as HttpMethod)}>
                    <SelectTrigger
                      className={cn('h-9 text-sm font-mono w-30', METHOD_COLOR[method])}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {HTTP_METHODS.map((httpMethod) => (
                        <SelectItem
                          key={httpMethod}
                          value={httpMethod}
                          className={cn('font-mono text-sm', METHOD_COLOR[httpMethod])}
                        >
                          {httpMethod}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="URL" className="flex-1 min-w-0">
                  <Input
                    {...register(`tools.${toolIndex}.url`)}
                    placeholder="https://api.example.com/endpoint"
                    className="h-9 text-sm font-mono w-full"
                  />
                </Field>
              </div>
              <Field label="Timeout (seconds)">
                <Input
                  type="number"
                  min={1}
                  max={120}
                  {...register(`tools.${toolIndex}.timeout`, { valueAsNumber: true })}
                  className="h-9 text-sm font-mono w-30"
                />
              </Field>
            </div>
          </div>

          {/* Auth headers */}
          <div>
            <SectionHeading>Auth headers</SectionHeading>

            <div className="space-y-2">
              {authFields.length > 0 && (
                <div className="flex items-center gap-2 mb-1 px-0.5">
                  <span className="text-[10px] text-muted-foreground/40 flex-2">Key</span>
                  <span className="text-[10px] text-muted-foreground/40 flex-3">Value</span>
                  <span className="w-8" />
                </div>
              )}

              {authFields.map((field, headerIndex) => (
                <AuthHeaderRow
                  key={field.id}
                  toolIndex={toolIndex}
                  headerIndex={headerIndex}
                  onRemove={() => removeAuth(headerIndex)}
                />
              ))}

              <Button
                variant="ghost"
                onClick={addAuthHeader}
                className="h-auto p-0 font-normal flex items-center gap-1.5 text-xs text-muted-foreground/50 hover:text-muted-foreground hover:bg-transparent transition-colors pt-1"
              >
                <Plus className="w-3.5 h-3.5" />
                Add header
              </Button>
            </div>
          </div>

          {/* Parameters */}
          <div>
            <SectionHeading>Parameters</SectionHeading>

            <p className="text-xs text-muted-foreground/50 mb-4 leading-relaxed">
              Define the arguments the model should collect and pass when calling this tool. Each
              parameter becomes a field in the JSON body or query string.
            </p>

            <ToolParameters toolIndex={toolIndex} />
          </div>
        </fieldset>
      </div>
    </div>
  );
}
