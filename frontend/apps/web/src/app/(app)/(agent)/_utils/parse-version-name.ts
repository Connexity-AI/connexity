export function parseVersionName(changeDescription: string | null | undefined): {
  name: string | null;
  description: string | null;
} {
  if (!changeDescription) return { name: null, description: null };
  const lines = changeDescription.split('\n');
  if (lines.length <= 1) return { name: lines[0] || null, description: null };
  return { name: lines[0] || null, description: lines.slice(1).join('\n').trim() || null };
}
