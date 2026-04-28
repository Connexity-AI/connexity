export const TABS = [
  { id: 'prompt', label: 'Prompt' },
  { id: 'tools', label: 'Tools' },
  { id: 'settings', label: 'Settings' },
] as const;

export type TabId = (typeof TABS)[number]['id'];

export function temperatureLabel(temperature: number) {
  if (temperature <= 0.2) return 'Deterministic';
  if (temperature <= 0.5) return 'Focused';
  if (temperature <= 0.8) return 'Balanced';
  if (temperature <= 1.2) return 'Creative';
  return 'Random';
}
