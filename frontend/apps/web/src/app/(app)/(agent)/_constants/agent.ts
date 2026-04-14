export const TABS = [
  { id: 'prompt', label: 'Prompt' },
  { id: 'tools', label: 'Tools' },
  { id: 'settings', label: 'Settings' },
] as const;

export type TabId = (typeof TABS)[number]['id'];

export const PROVIDERS = [
  {
    group: 'OpenAI',
    models: ['gpt-4.1', 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  },
  {
    group: 'Anthropic',
    models: [
      'claude-opus-4-5',
      'claude-sonnet-4-5',
      'claude-haiku-3-5',
      'claude-3-opus',
      'claude-3-sonnet',
    ],
  },
  {
    group: 'Google',
    models: ['gemini-2.5-pro', 'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  },
  {
    group: 'Mistral',
    models: ['mistral-large-latest', 'mistral-medium', 'mistral-small', 'codestral-latest'],
  },
  {
    group: 'Groq',
    models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
  },
  { group: 'Cohere', models: ['command-r-plus', 'command-r', 'command-light'] },
] as const;

export const DEFAULT_MODELS: Record<string, string> = {
  OpenAI: 'gpt-4.1',
  Anthropic: 'claude-opus-4-5',
  Google: 'gemini-2.5-pro',
  Mistral: 'mistral-large-latest',
  Groq: 'llama-3.3-70b-versatile',
  Cohere: 'command-r-plus',
};

export function temperatureLabel(temperature: number) {
  if (temperature <= 0.2) return 'Deterministic';
  if (temperature <= 0.5) return 'Focused';
  if (temperature <= 0.8) return 'Balanced';
  if (temperature <= 1.2) return 'Creative';
  return 'Random';
}
