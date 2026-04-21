export function scoreColor(score: number | null | undefined): {
  text: string;
  bar: string;
} {
  const s = score ?? 0;
  if (s >= 80) return { text: 'text-green-400', bar: 'bg-green-400' };
  if (s >= 60) return { text: 'text-yellow-400', bar: 'bg-yellow-400' };
  return { text: 'text-red-400', bar: 'bg-red-400' };
}

export function roundScore(score: number | null | undefined): number | null {
  if (score === null || score === undefined) return null;
  return Math.round(score);
}
