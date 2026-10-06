import { Platform } from '@/client/types.gen';

import type { AgentProviderTarget } from './agent-provider-target';
import { isPlatformIntegration } from './environment-platform-utils';

export type AgentEnvironmentFormMode = 'loading' | 'webhook' | 'integration';

export function getAgentEnvironmentFormMode(
  agent: AgentProviderTarget | undefined,
  isAgentLoading: boolean
): AgentEnvironmentFormMode {
  if (isAgentLoading) {
    return 'loading';
  }
  if (!agent?.platform || agent.platform === Platform.WEBHOOK) {
    return 'webhook';
  }
  if (isPlatformIntegration(agent.platform)) {
    return 'integration';
  }
  return 'webhook';
}
