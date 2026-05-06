import type { MetricTier, ScoreType } from '@/client/types.gen';

export const TIER_META: Record<
  MetricTier,
  { label: string; color: string; dot: string; description: string }
> = {
  execution: {
    label: 'Execution',
    color: 'bg-blue-500/15 text-blue-400 border-blue-500/20',
    dot: 'bg-blue-400',
    description: 'Tool usage, parameter accuracy, result handling',
  },
  knowledge: {
    label: 'Knowledge',
    color: 'bg-purple-500/15 text-purple-400 border-purple-500/20',
    dot: 'bg-purple-400',
    description: 'Factual grounding, instruction & policy adherence',
  },
  process: {
    label: 'Process',
    color: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
    dot: 'bg-amber-400',
    description: 'Information gathering, conversation flow, error recovery',
  },
  delivery: {
    label: 'Delivery',
    color: 'bg-teal-500/15 text-teal-400 border-teal-500/20',
    dot: 'bg-teal-400',
    description: 'Tone, conciseness, TTS-friendliness, phrasing',
  },
};

export const SCORE_TYPE_META: Record<ScoreType, { label: string; color: string }> = {
  scored: { label: 'Scored 0–5', color: 'bg-indigo-500/15 text-indigo-400' },
  binary: { label: 'Binary', color: 'bg-muted text-muted-foreground' },
};

export const TIERS: MetricTier[] = ['execution', 'knowledge', 'process', 'delivery'];
export const SCORE_TYPES: ScoreType[] = ['scored', 'binary'];

export type TierFilter = 'all' | MetricTier;
export type ScoreFilter = 'all' | ScoreType;

export const TIER_FILTERS: TierFilter[] = ['all', ...TIERS];
export const SCORE_FILTERS: ScoreFilter[] = ['all', ...SCORE_TYPES];

export function isValidSnakeCase(s: string): boolean {
  return /^[a-z][a-z0-9_]*$/.test(s);
}
