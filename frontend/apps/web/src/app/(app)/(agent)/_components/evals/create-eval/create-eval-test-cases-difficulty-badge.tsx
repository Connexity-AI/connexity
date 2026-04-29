'use client';

import { AlertTriangle } from 'lucide-react';

interface DifficultyBadgeProps {
  difficulty: string | null | undefined;
}

export function DifficultyBadge({ difficulty }: DifficultyBadgeProps) {
  if (difficulty === 'hard') {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-orange-500/10 px-1.5 py-0.5 text-[10px] text-orange-400">
        <AlertTriangle className="h-2.5 w-2.5" />
        Hard
      </span>
    );
  }

  return (
    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
      Normal
    </span>
  );
}
