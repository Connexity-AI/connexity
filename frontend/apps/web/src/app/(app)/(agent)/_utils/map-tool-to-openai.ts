import type { AgentToolValues } from '@/app/(app)/(agent)/_schemas/agent-form';

/**
 * Serializes agent editor tool rows to persisted OpenAI function tools + optional
 * `platform_config` (implementation-only; mock vs live comes from RunConfig.tool_mode).
 */
export function mapToolToOpenAI(tool: AgentToolValues): Record<string, unknown> {
  const hasEndpoint = tool.url.trim().length > 0;

  const headers = tool.authHeaders.reduce<Record<string, string>>((accumulator, header) => {
    if (header.key.trim()) accumulator[header.key] = header.value;
    return accumulator;
  }, {});

  return {
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: {
        type: 'object',
        properties: Object.fromEntries(
          tool.parameters.map((parameter) => [
            parameter.name,
            { type: parameter.type, description: parameter.description },
          ])
        ),
        required: tool.parameters
          .filter((parameter) => parameter.required)
          .map((parameter) => parameter.name),
      },
    },
    ...(hasEndpoint && {
      platform_config: {
        implementation: {
          type: 'http_webhook',
          url: tool.url,
          method: tool.method,
          headers: Object.keys(headers).length > 0 ? headers : undefined,
          timeout_ms: tool.timeout * 1000,
        },
      },
    }),
  };
}
