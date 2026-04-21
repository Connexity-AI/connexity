'use client';

import { cn } from '@workspace/ui/lib/utils';

import { AI_GENERATION_STAGES } from './use-ai-test-case-generation';

type StageStatus = 'done' | 'active' | 'pending';

const STAGE_ROW_CLASS: Record<StageStatus, string> = {
  done: 'text-muted-foreground',
  active: 'text-foreground',
  pending: 'text-muted-foreground/30',
};

const STAGE_DOT_CLASS: Record<StageStatus, string> = {
  done: 'bg-violet-400',
  active: 'animate-pulse bg-violet-400',
  pending: 'bg-muted-foreground/20',
};

function getStageStatus(index: number, currentIndex: number): StageStatus {
  if (index < currentIndex) return 'done';
  if (index === currentIndex) return 'active';
  return 'pending';
}

interface AddTestCaseAiGeneratingPhaseProps {
  stageIndex: number;
  progress: number;
}

export function AddTestCaseAiGeneratingPhase({
  stageIndex,
  progress,
}: AddTestCaseAiGeneratingPhaseProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {AI_GENERATION_STAGES[stageIndex]?.label}
          </span>

          <span className="text-xs tabular-nums text-muted-foreground/50">{progress}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-accent">
          <div
            className="h-full rounded-full bg-violet-500 transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <div className="space-y-1.5">
        {AI_GENERATION_STAGES.map((stage, i) => {
          const status = getStageStatus(i, stageIndex);

          return (
            <div
              key={stage.label}
              className={cn(
                'flex items-center gap-2 text-[11px] transition-colors',
                STAGE_ROW_CLASS[status]
              )}
            >
              <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', STAGE_DOT_CLASS[status])} />
              {stage.label}
            </div>
          );
        })}
      </div>
    </div>
  );
}
