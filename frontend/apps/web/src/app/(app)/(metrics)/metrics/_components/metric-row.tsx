'use client';

import { Checkbox } from '@workspace/ui/components/ui/checkbox';
import { Switch } from '@workspace/ui/components/ui/switch';
import { cn } from '@workspace/ui/lib/utils';

import { ScoreTypeBadge, TierBadge } from './metric-badges';

import type { MetricRecord } from './metric-types';

export function MetricRow({
  metric,
  isSelected,
  isChecked,
  onSelect,
  onCheck,
  onToggleActive,
}: {
  metric: MetricRecord;
  isSelected: boolean;
  isChecked: boolean;
  onSelect: (id: string) => void;
  onCheck: (id: string, checked: boolean) => void;
  onToggleActive: (id: string, active: boolean) => void;
}) {
  const active = !metric.is_draft;
  const isPredefined = !!metric.is_predefined;

  return (
    <div
      onClick={() => onSelect(metric.id)}
      className={cn(
        'grid grid-cols-[32px_2fr_1fr_1fr_72px] items-center border-b border-border cursor-pointer transition-colors px-5 py-0 min-h-[44px]',
        isSelected ? 'bg-accent/60' : 'hover:bg-accent/30'
      )}
    >
      <div onClick={(e) => e.stopPropagation()} className="flex items-center">
        <Checkbox
          checked={isChecked}
          onCheckedChange={(c) => onCheck(metric.id, c === true)}
        />
      </div>

      <div className="py-2.5 pr-4 min-w-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <p className="text-xs font-mono text-foreground truncate">
            {metric.display_name || metric.name || (
              <span className="text-muted-foreground italic">unnamed</span>
            )}
          </p>
          {isPredefined && (
            <span className="px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider border border-border/60 bg-accent/40 text-muted-foreground/80 shrink-0">
              Predefined
            </span>
          )}
        </div>
        {metric.description && (
          <p className="text-[10px] text-muted-foreground/50 truncate mt-0.5 leading-snug">
            {metric.description}
          </p>
        )}
      </div>

      <div className="py-2.5 pr-4">
        <TierBadge tier={metric.tier} />
      </div>

      <div className="py-2.5">
        <ScoreTypeBadge type={metric.score_type} />
      </div>

      <div className="py-2.5 flex items-center" onClick={(e) => e.stopPropagation()}>
        <Switch
          checked={active}
          onCheckedChange={(v) => onToggleActive(metric.id, v)}
          className="h-4 w-7 [&>span]:h-3 [&>span]:w-3 [&>span]:data-[state=checked]:translate-x-3 data-[state=checked]:bg-green-500/80"
        />
      </div>
    </div>
  );
}
