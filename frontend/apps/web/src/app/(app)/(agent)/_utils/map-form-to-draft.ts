import type { AgentDraftUpdate } from '@/client/types.gen';
import type { AgentFormValues } from '@/app/(app)/(agent)/_schemas/agent-form';
import { mapToolToOpenAI } from '@/app/(app)/(agent)/_utils/map-tool-to-openai';

export function mapFormToDraft(data: AgentFormValues): AgentDraftUpdate {
  return {
    system_prompt: data.prompt,
    agent_model: data.model,
    agent_provider: data.provider,
    tools: data.tools.map(mapToolToOpenAI),
    agent_temperature: data.temperature,
  };
}
