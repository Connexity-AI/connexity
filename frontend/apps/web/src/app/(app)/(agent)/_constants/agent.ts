/** Sentinel agent_model the backend sets for Retell conversation-flow agents. */
export const CONVERSATION_FLOW_AGENT_MODEL = 'conversation-flow';

export function isConversationFlowAgent(
  agent: { agent_model?: string | null } | null | undefined
): boolean {
  return agent?.agent_model === CONVERSATION_FLOW_AGENT_MODEL;
}

const ALL_TABS = [
  { id: 'prompt', label: 'Prompt' },
  { id: 'info', label: 'Info' },
  { id: 'requirements', label: 'Requirements' },
  { id: 'tools', label: 'Tools' },
  { id: 'settings', label: 'Settings' },
] as const;

export type TabId = (typeof ALL_TABS)[number]['id'];

/**
 * Tabs visible for a given agent. Conversation-flow agents are read-only
 * bindings — there is no single editable prompt — so they get an Info tab in
 * place of Prompt. Everything else keeps the standard prompt-editing layout.
 */
export function visibleTabsForAgent(
  agent: { agent_model?: string | null } | null | undefined
): readonly { id: TabId; label: string }[] {
  const hiddenId: TabId = isConversationFlowAgent(agent) ? 'prompt' : 'info';
  return ALL_TABS.filter((tab) => tab.id !== hiddenId);
}

export function defaultTabForAgent(
  agent: { agent_model?: string | null } | null | undefined
): TabId {
  return isConversationFlowAgent(agent) ? 'info' : 'prompt';
}

export function temperatureLabel(temperature: number) {
  if (temperature <= 0.2) return 'Deterministic';
  if (temperature <= 0.5) return 'Focused';
  if (temperature <= 0.8) return 'Balanced';
  if (temperature <= 1.2) return 'Creative';
  return 'Random';
}
