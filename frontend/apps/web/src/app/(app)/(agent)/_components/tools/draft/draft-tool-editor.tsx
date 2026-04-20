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

import { DraftAuthHeaderRow } from '@/app/(app)/(agent)/_components/tools/draft/draft-auth-header-row';
import { DraftToolEditorHeader } from '@/app/(app)/(agent)/_components/tools/draft/draft-tool-editor-header';
import { DraftToolParameters } from '@/app/(app)/(agent)/_components/tools/draft/draft-tool-parameters';
import { Field, SectionHeading } from '@/app/(app)/(agent)/_components/tools/tool-editor-field';
import { useDraftTool } from '@/app/(app)/(agent)/_hooks/use-draft-tool';

import type { AgentToolValues, HttpMethod } from '@/app/(app)/(agent)/_schemas/agent-form';

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

const METHOD_COLOR: Record<HttpMethod, string> = {
  GET: 'text-green-400',
  POST: 'text-blue-400',
  PUT: 'text-amber-400',
  PATCH: 'text-purple-400',
  DELETE: 'text-red-400',
};

interface DraftToolEditorProps {
  onSave: (tool: AgentToolValues) => void;
  onBack: () => void;
}

export function DraftToolEditor({ onSave, onBack }: DraftToolEditorProps) {
  const {
    draft,
    set,
    setToolName,
    setMethod,
    addAuthHeader,
    removeAuth,
    updateAuthHeader,
    addParameter,
    removeParameter,
    updateParameter,
  } = useDraftTool();

  return (
    <div className="flex flex-col h-full w-full bg-background">
      <DraftToolEditorHeader toolName={draft.name} onBack={onBack} onSave={() => onSave(draft)} />

      <div className="flex-1 overflow-auto">
        <div className="px-8 py-6 space-y-8">
          {/* Identity */}
          <div>
            <SectionHeading>Identity</SectionHeading>
            <div className="space-y-4">
              <Field
                label="Tool name"
                hint="snake_case — the model uses this name to reference the tool"
              >
                <Input
                  value={draft.name}
                  onChange={(event) =>
                    setToolName(event.target.value.replace(/\s/g, '_').toLowerCase())
                  }
                  placeholder="e.g. get_available_time"
                  className="h-9 text-sm font-mono"
                />
              </Field>

              <Field
                label="Description"
                hint="The model reads this to decide when to invoke the tool. Be specific about the trigger condition."
              >
                <Textarea
                  value={draft.description}
                  onChange={(event) => set('description', event.target.value)}
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
                  <Select
                    value={draft.method}
                    onValueChange={(value) => setMethod(value as HttpMethod)}
                  >
                    <SelectTrigger
                      className={cn('h-9 text-sm font-mono w-[120px]', METHOD_COLOR[draft.method])}
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
                    value={draft.url}
                    onChange={(event) => set('url', event.target.value)}
                    placeholder="https://api.example.com/endpoint"
                    className="h-9 text-sm font-mono w-full"
                  />
                </Field>
              </div>

              <Field label="Timeout (seconds)">
                <Input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={draft.timeout}
                  onChange={(event) => {
                    const parsed = parseInt(event.target.value, 10);
                    set(
                      'timeout',
                      Math.min(120, Math.max(1, Number.isFinite(parsed) ? parsed : 3))
                    );
                  }}
                  className="h-9 text-sm font-mono w-30"
                />
              </Field>
            </div>
          </div>

          {/* Auth headers */}
          <div>
            <SectionHeading>Auth headers</SectionHeading>
            <div className="space-y-2">
              {draft.authHeaders.length > 0 && (
                <div className="flex items-center gap-2 mb-1 px-0.5">
                  <span className="text-[10px] text-muted-foreground/40 flex-2">Key</span>
                  <span className="text-[10px] text-muted-foreground/40 flex-3">Value</span>
                  <span className="w-8" />
                </div>
              )}
              {draft.authHeaders.map((header, index) => (
                <DraftAuthHeaderRow
                  key={header.id}
                  header={header}
                  onChange={(patch) => updateAuthHeader(index, patch)}
                  onRemove={() => removeAuth(index)}
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
            <DraftToolParameters
              parameters={draft.parameters}
              onAdd={addParameter}
              onUpdate={updateParameter}
              onRemove={removeParameter}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
