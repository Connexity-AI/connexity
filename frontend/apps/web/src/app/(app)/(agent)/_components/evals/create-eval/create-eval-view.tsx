'use client';
'use no memo';

import { useState } from 'react';

import { Form } from '@workspace/ui/components/ui/form';

import { CreateEvalReadOnlyProvider } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-readonly-context';
import { CreateEvalSaveActions } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-save-actions';
import { CreateEvalTopbar } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-topbar';
import { UrlGenerator } from '@/common/url-generator/url-generator';
import { JudgeSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-judge-section';
import { PersonaSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-persona-section';
import { RunConfigSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-run-config-section';
import { TestCasesSection } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-test-cases-section';
import { useCreateEvalForm } from '@/app/(app)/(agent)/_components/evals/create-eval/use-create-eval-form';

import type { EvalConfigMemberPublic, EvalConfigPublic } from '@/client/types.gen';

function defaultConfigName() {
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  return `Eval Config ${today}`;
}

interface CreateEvalViewProps {
  agentId: string;
  initialTestCaseIds?: string[];
  readOnly?: boolean;
  initialConfig?: EvalConfigPublic;
  initialMembers?: EvalConfigMemberPublic[];
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

              <CreateEvalTopbar.NameInput
                value={name}
                disabled={readOnly}
                onChange={(v) => form.setValue('name', v, { shouldDirty: true })}
              />
            </CreateEvalTopbar.Leading>

            <CreateEvalTopbar.Actions>
              <CreateEvalTopbar.CancelButton
                agentId={agentId}
                href={backHref}
                label={readOnly ? 'Close' : 'Cancel'}
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
              {submitError ? (
                <p className="text-xs text-destructive" role="alert">
                  {submitError}
                </p>
              ) : null}
              <RunConfigSection />
              <TestCasesSection agentId={agentId} />
              <JudgeSection metrics={metrics} />
              <PersonaSection />
            </div>
          </form>
        </div>
      </Form>
    </CreateEvalReadOnlyProvider>
  );
}
