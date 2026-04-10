'use client';

import { useFormContext } from 'react-hook-form';

import { FormControl, FormField, FormItem, FormMessage } from '@workspace/ui/components/ui/form';
import { TabsContent } from '@workspace/ui/components/ui/tabs';
import { Textarea } from '@workspace/ui/components/ui/textarea';

import { DiffControls } from '@/app/(app)/(agent)/_components/diff-controls';
import { DiffView } from '@/app/(app)/(agent)/_components/diff-view';
import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';
import { useAgentVersions } from '@/app/(app)/(agent)/_hooks/use-agent-versions';

import type { DiffVersionId } from '@/app/(app)/(agent)/_context/versions-context';
import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';

export function PromptTab() {
  const form = useFormContext<AgentFormValues>();
  const { isReadOnly, agentId } = useAgentEditFormActions();
  const { showDiff, diffFromVersion, diffToVersion, setDiffFromVersion, setDiffToVersion } =
    useVersions();
  const { data: versionsData } = useAgentVersions(agentId);
  const versions = versionsData?.data ?? [];

  const resolveContent = (id: DiffVersionId): string => {
    if (id === 'draft') {
      return form.getValues().prompt ?? '';
    }

    const match = versions.find((v) => v.version === id);
    return match?.system_prompt ?? '';
  };

  const diffMode = showDiff && isReadOnly;

  if (diffMode) {
    return (
      <TabsContent value="prompt" className="flex-1 mt-0 p-6 flex flex-col min-h-0">
        <div className="flex-1 flex flex-col min-h-0">
          <DiffControls
            versions={versions}
            fromVersion={diffFromVersion}
            toVersion={diffToVersion}
            onFromChange={setDiffFromVersion}
            onToChange={setDiffToVersion}
          />
          <DiffView
            fromContent={resolveContent(diffFromVersion)}
            toContent={resolveContent(diffToVersion)}
          />
        </div>
      </TabsContent>
    );
  }

  return (
    <TabsContent value="prompt" className="flex-1 mt-0 p-6 flex flex-col min-h-0">
      <FormField
        control={form.control}
        name="prompt"
        render={({ field }) => (
          <FormItem className="flex-1 flex flex-col min-h-0">
            <FormControl>
              <Textarea
                {...field}
                placeholder="Enter your prompt here..."
                className="w-full flex-1 resize-none min-h-0"
                readOnly={isReadOnly}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </TabsContent>
  );
}
