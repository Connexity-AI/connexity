import { TextRuntimeKind } from '@/client/types.gen';

import type { RunConfigOutput } from '@/client/types.gen';

type ToolCallModeBadgeTone = 'mock' | 'live' | 'na';

export interface ToolCallModeBadge {
  label: 'Mock' | 'Live' | 'N/A';
  tone: ToolCallModeBadgeTone;
}

export function getToolCallModeBadge(
  runConfig: RunConfigOutput | null | undefined
): ToolCallModeBadge {
  const runtimeKind = runConfig?.runtime?.kind ?? TextRuntimeKind.CONNEXITY;
  if (runtimeKind !== TextRuntimeKind.CONNEXITY) {
    return { label: 'N/A', tone: 'na' };
  }

  const toolMode = runConfig?.tool_mode ?? 'mock';
  if (toolMode === 'live') {
    return { label: 'Live', tone: 'live' };
  }

  return { label: 'Mock', tone: 'mock' };
}
