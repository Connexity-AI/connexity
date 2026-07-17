'use client';

import { useAgentEditFormActions } from '@/app/(app)/(agent)/_context/agent-edit-form-context';
import { useAgentFlowStaleness } from '@/app/(app)/(agent)/_hooks/use-agent-flow-staleness';

/**
 * Fires the Retell flow-staleness check once per agent per browser session.
 * Mounted once at the agent layout level (not per-tab) so switching between
 * Info / Requirements / Test Cases / Eval Runs doesn't re-trigger it — the
 * result is cached (staleTime: Infinity) and read from wherever needs it,
 * e.g. the Info tab badge, via the same query key.
 *
 * Renders nothing; this is a side-effect-only mount.
 */
export function AgentFlowStalenessWatcher() {
  const { agentId, agent } = useAgentEditFormActions();
  useAgentFlowStaleness(agentId, agent);
  return null;
}
