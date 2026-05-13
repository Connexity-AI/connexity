import { EvaluationEngineKind } from '@/client/types.gen';

import type { RunConfigOutput } from '@/client/types.gen';

type ToolCallModeBadgeTone = 'mock' | 'live' | 'na';

export interface ToolCallModeBadge {
  label: 'Mock' | 'Live' | 'N/A';
  tone: ToolCallModeBadgeTone;
}

export function getToolCallModeBadge(
  runConfig: RunConfigOutput | null | undefined
): ToolCallModeBadge {
  const engineKind = runConfig?.evaluation_engine?.kind ?? EvaluationEngineKind.CONNEXITY;
  if (engineKind !== EvaluationEngineKind.CONNEXITY) {
    return { label: 'N/A', tone: 'na' };
  }

  const toolMode = runConfig?.tool_mode ?? 'mock';
  if (toolMode === 'live') {
    return { label: 'Live', tone: 'live' };
  }

  return { label: 'Mock', tone: 'mock' };
}
