'use client';
'use no memo';

import { useState } from 'react';
import { AlertCircle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@workspace/ui/components/ui/alert';
import { Form } from '@workspace/ui/components/ui/form';

import { CreateEvalReadOnlyProvider } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import { CreateEvalSaveActions } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-save-actions';
import { CreateEvalTopbar } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-topbar';
import { EditableEvalConfigName } from '@/app/(app)/(agent)/_components/evals/eval-configs/editable-eval-config-name';
import { RunEvalConfigButton } from '@/app/(app)/(agent)/_components/evals/run-eval-config-button';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { JudgeSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-judge-section';
import { PassThresholdsSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-pass-thresholds-section';
import { PersonaSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-persona-section';
import {
  RuntimeSection,
  RunConfigSection,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-run-config-section';
import { TestCasesSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-section';
import { useCreateEvalForm } from '@/app/(app)/(agent)/_components/evals/create-eval/use-create-eval-form';
import { useAgent } from '@/app/(app)/(agent)/_hooks/use-agent';

import type { EvalConfigMemberPublic, EvalConfigPublic } from '@/client/types.gen';

function defaultConfigName() {
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  return `Eval Config ${today}`;
}

interface DetailPageRunButtonProps {
  readOnly: boolean;
  initialConfig: EvalConfigPublic | undefined;
  agentId: string;
}

function DetailPageRunButton({
  readOnly,
  initialConfig,
  agentId,
}: DetailPageRunButtonProps) {
  if (!readOnly) return null;
  if (!initialConfig) return null;

  return <RunEvalConfigButton agentId={agentId} evalConfigId={initialConfig.id} />;
}

interface CreateEvalViewProps {
  agentId: string;
  initialTestCaseIds?: string[];
  readOnly?: boolean;
  initialConfig?: EvalConfigPublic;
  initialMembers?: EvalConfigMemberPublic[];
}

const TOOL_CALLS_ENGINE_ERROR =
  "Tool calls are only supported with the Connexity runtime. Remove expected_tool_calls from the linked test cases, or switch the runtime to 'connexity'.";

function SubmitErrorAlert({ message }: { message: string | null }) {
  if (message === null) {
    return null;
  }

  if (message === '') {
    return null;
  }

  if (message === TOOL_CALLS_ENGINE_ERROR) {
    return (
      <Alert
        variant="default"
        className="border border-dashed border-yellow-400! bg-yellow-500/5 text-yellow-300"
      >
        <AlertCircle className="h-4 w-4 text-yellow-300!" />
        <AlertTitle>Tool calls require Connexity runtime</AlertTitle>
        <AlertDescription>
          This config includes test cases with expected tool calls. Switch runtime to
          <span className="font-medium"> Connexity</span>, or remove expected tool calls from the
          selected test cases.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Could not save eval config</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

export function CreateEvalView({
  agentId,
  initialTestCaseIds,
  readOnly = false,
  initialConfig,
  initialMembers,
}: CreateEvalViewProps) {
  const [initialName] = useState(() => initialConfig?.name ?? defaultConfigName());

  const { form, metrics, submitSave, submitSaveAndRun, isPending, submitError } =
    useCreateEvalForm({
      agentId,
      initialName,
      initialTestCaseIds,
      initialConfig,
      initialMembers,
    });

  const { data: agent } = useAgent(agentId);

  const name = form.watch('name');
  const backHref = readOnly ? UrlGenerator.agentEvalsConfigs(agentId) : undefined;

  return (
    <CreateEvalReadOnlyProvider readOnly={readOnly}>
      <Form {...form}>
        <div className="flex flex-1 min-h-0 flex-col">
          <CreateEvalTopbar>
            <CreateEvalTopbar.Leading>
              <CreateEvalTopbar.BackLink agentId={agentId} href={backHref} />

              <CreateEvalTopbar.Separator />

              {readOnly && initialConfig ? (
                <EditableEvalConfigName
                  evalConfigId={initialConfig.id}
                  agentId={agentId}
                  name={name}
                  onRenamed={(n) => form.setValue('name', n, { shouldDirty: false })}
                />
              ) : (
                <CreateEvalTopbar.NameInput
                  value={name}
                  disabled={readOnly}
                  onChange={(v) => form.setValue('name', v, { shouldDirty: true })}
                />
              )}
            </CreateEvalTopbar.Leading>

            <CreateEvalTopbar.Actions>
              <CreateEvalTopbar.CancelButton
                agentId={agentId}
                href={backHref}
                label={readOnly ? 'Close' : 'Cancel'}
              />
              <DetailPageRunButton
                readOnly={readOnly}
                initialConfig={initialConfig}
                agentId={agentId}
              />
              <CreateEvalSaveActions
                readOnly={readOnly}
                isPending={isPending}
                onSave={submitSave}
                onSaveAndRun={submitSaveAndRun}
              />
            </CreateEvalTopbar.Actions>
          </CreateEvalTopbar>

          <form onSubmit={(e) => e.preventDefault()} className="flex-1 overflow-auto">
            <div className="mx-auto max-w-2xl space-y-4 px-6 py-6">
              <SubmitErrorAlert message={submitError} />
              <RunConfigSection />
              <TestCasesSection agentId={agentId} />
              <JudgeSection metrics={metrics} />
              <PassThresholdsSection />
              <PersonaSection />
              <RuntimeSection
                agentId={agentId}
                agentMode={agent?.mode ?? null}
                agentTools={agent?.tools ?? null}
                defaultToBackendOption={!initialConfig}
              />
            </div>
          </form>
        </div>
      </Form>
    </CreateEvalReadOnlyProvider>
  );
}
