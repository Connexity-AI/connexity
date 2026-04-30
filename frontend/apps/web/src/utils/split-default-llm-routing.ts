import type { LlmModelsPublic } from '@/client/types.gen';

/**
 * Last-resort LiteLLM routing id when `/api/v1/config` is unreachable.
 * Must match backend Settings defaults (`LLM_DEFAULT_PROVIDER`/`LLM_DEFAULT_MODEL`).
 */
export const BOOTSTRAP_DEFAULT_LLM_ROUTE = 'openai/gpt-4.1' as const;

/** Split `provider/local_model` into fields used by legacy agent/eval forms. */
export function splitDefaultLlmRouting(defaultLlmRoute: string): {
  provider: string;
  model: string;
} {
  const idx = defaultLlmRoute.indexOf('/');
  if (idx <= 0) {
    return { provider: 'openai', model: defaultLlmRoute };
  }
  return {
    provider: defaultLlmRoute.slice(0, idx),
    model: defaultLlmRoute.slice(idx + 1),
  };
}

/** Minimal catalog so `LlmModelPicker` works when `GET /config/llm-models` fails. */
export function minimalLlmModelsFromRoute(defaultRoute: string): LlmModelsPublic {
  const { provider, model } = splitDefaultLlmRouting(defaultRoute);
  const providerLabel = provider === 'openai' ? 'OpenAI' : provider;
  return {
    default_model: defaultRoute,
    count: 1,
    data: [
      {
        provider,
        label: providerLabel,
        default_model: defaultRoute,
        models: [
          {
            id: defaultRoute,
            provider,
            provider_label: providerLabel,
            model,
            label: model,
            is_default: true,
            is_recommended: true,
            max_input_tokens: null,
            max_output_tokens: null,
          },
        ],
      },
    ],
  };
}
