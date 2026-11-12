import { Circle, CircleCheck } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { ConnectCommand } from '@/components/readiness/connect-command';

import type { ReadinessPublic, ReadinessStep } from '@/client/types.gen';
import type { FC } from 'react';

const StepIcon: FC<{ state: ReadinessStep['state'] }> = ({ state }) => {
  if (state === 'done') return <CircleCheck className="size-4 text-passed" aria-label="Done" />;
  if (state === 'in_progress')
    return (
      <span
        aria-label="In progress"
        className="size-4 animate-spin rounded-full border-2 border-border-control/40 border-t-ink motion-reduce:animate-none"
      />
    );
  return <Circle className="size-4 text-border-control" aria-label="Not started" />;
};

interface Props {
  readiness: ReadinessPublic;
}

/** Readiness while the first scan is not done (designs/screens/Connexity Onboarding.dc.html). */
export const ReadinessView: FC<Props> = ({ readiness }) => {
  const assistant = readiness.steps.find((step) => step.key === 'assistant');
  const assistantConnected = assistant?.state === 'done';

  return (
    <div className="flex max-w-[760px] flex-col gap-6">
      <div className="flex min-h-10 items-center justify-between gap-4">
        <h1 className="m-0 text-title font-medium text-ink">Readiness</h1>
        <span className="text-title font-medium text-ink">{readiness.percent}%</span>
      </div>

      <div className="-mt-3 flex flex-col gap-1.5">
        <div
          className="h-1.5 overflow-hidden rounded-[3px] bg-unchecked-bg"
          role="progressbar"
          aria-valuenow={readiness.percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Readiness"
        >
          <div
            className="h-full rounded-[3px] bg-ink transition-[width] duration-300"
            style={{ width: `${readiness.percent}%` }}
          />
        </div>
        <span className="text-label text-ink-muted">
          {readiness.done} of {readiness.total} steps
        </span>
      </div>

      <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
        <div className="px-6 pt-4 pb-3">
          <h2 className="m-0 text-body font-medium text-ink">Getting started</h2>
        </div>
        {readiness.steps.map((step) => (
          <div key={step.key} className="flex flex-col gap-2.5 border-t border-hairline px-6 py-3">
            <div className="grid grid-cols-[16px_minmax(0,1fr)_auto] items-center gap-3.5">
              <span className="flex">
                <StepIcon state={step.state} />
              </span>
              <span
                className={cn(
                  step.state === 'not_started' ? 'text-ink-secondary' : 'text-ink',
                  step.state === 'in_progress' && 'font-medium'
                )}
              >
                {step.name}
              </span>
              <span className="text-right text-label whitespace-nowrap text-ink-secondary">
                {step.detail ?? ''}
              </span>
            </div>
            {step.key === 'assistant' && !assistantConnected && readiness.connect_command && (
              <ConnectCommand command={readiness.connect_command} />
            )}
            {step.key === 'assistant' && !assistantConnected && !readiness.connect_command && (
              <span className="ml-[30px] text-label text-ink-secondary">
                The MCP address is not configured on this deployment, so there is no command to show
                yet.
              </span>
            )}
          </div>
        ))}
      </section>

    </div>
  );
};

export default ReadinessView;
