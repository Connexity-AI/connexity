import type { LlmModelsPublic } from '@/client/types.gen';

export const DEFAULT_LLM_PROVIDER = 'openai';
export const DEFAULT_LLM_MODEL = 'gpt-4.1';
export const DEFAULT_LLM_MODEL_ID = `${DEFAULT_LLM_PROVIDER}/${DEFAULT_LLM_MODEL}`;

export const FALLBACK_LLM_MODELS: LlmModelsPublic = {
  default_model: DEFAULT_LLM_MODEL_ID,
  count: 2,
  data: [
    {
      provider: DEFAULT_LLM_PROVIDER,
      label: 'OpenAI',
      default_model: DEFAULT_LLM_MODEL_ID,
      models: [
        {
          id: DEFAULT_LLM_MODEL_ID,
          provider: DEFAULT_LLM_PROVIDER,
          provider_label: 'OpenAI',
          model: DEFAULT_LLM_MODEL,
          label: DEFAULT_LLM_MODEL,
          is_default: true,
          is_recommended: true,
          max_input_tokens: 1047576,
          max_output_tokens: 32768,
        },
        {
          id: 'openai/gpt-4o-mini',
          provider: DEFAULT_LLM_PROVIDER,
          provider_label: 'OpenAI',
          model: 'gpt-4o-mini',
          label: 'gpt-4o-mini',
          is_default: false,
          is_recommended: true,
          max_input_tokens: 128000,
          max_output_tokens: 16384,
        },
      ],
    },
  ],
};
