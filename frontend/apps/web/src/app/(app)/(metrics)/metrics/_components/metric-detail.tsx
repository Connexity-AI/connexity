'use client';

import { useEffect, useState } from 'react';

import { Button } from '@workspace/ui/components/ui/button';
import { Input } from '@workspace/ui/components/ui/input';
import { Switch } from '@workspace/ui/components/ui/switch';
import { Textarea } from '@workspace/ui/components/ui/textarea';
import { cn } from '@workspace/ui/lib/utils';
import { Check, Trash2, X } from 'lucide-react';

import { ScoreTypeBadge, TierBadge } from './metric-badges';
import {
  SCORE_TYPES,
  SCORE_TYPE_META,
  TIERS,
  TIER_META,
  isValidSnakeCase,
} from './metric-meta';

import type { MetricRecord, MetricUpdatePatch } from './metric-types';
import type { MetricTier, ScoreType } from '@/client/types.gen';

export type MetricDraft = {
  id: string | null;
  name: string;
  display_name: string;
  description: string;
  tier: MetricTier;
  score_type: ScoreType;
  rubric: string;
  default_weight: number;
  active: boolean;
  is_predefined: boolean;
};

export function metricToDraft(metric: MetricRecord): MetricDraft {
  return {
    id: metric.id,
    name: metric.name,
    display_name: metric.display_name,
    description: metric.description ?? '',
    tier: metric.tier,
    score_type: metric.score_type,
    rubric: metric.rubric,
    default_weight: metric.default_weight ?? 1.0,
    active: !metric.is_draft,
    is_predefined: !!metric.is_predefined,
  };
}

export function newDraft(): MetricDraft {
  return {
    id: null,
    name: '',
    display_name: '',
    description: '',
    tier: 'execution',
    score_type: 'scored',
    rubric: '',
    default_weight: 1.0,
    active: true,
    is_predefined: false,
  };
}

export function MetricDetail({
  source,
  saved,
  saving,
  onSave,
  onDelete,
  onClose,
}: {
  source: MetricDraft;
  saved: boolean;
  saving: boolean;
  onSave: (patch: MetricUpdatePatch, draft: MetricDraft) => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const [name, setName] = useState(source.name);
  const [displayName, setDisplayName] = useState(source.display_name);
  const [description, setDescription] = useState(source.description);
  const [tier, setTier] = useState<MetricTier>(source.tier);
  const [scoreType, setScoreType] = useState<ScoreType>(source.score_type);
  const [rubric, setRubric] = useState(source.rubric);
  // Stored as string so the user can type intermediate values like "0." while
  // editing; parsed to a float on save and validated against the >= 0 backend rule.
  const [defaultWeight, setDefaultWeight] = useState(String(source.default_weight));
  const [active, setActive] = useState(source.active);

  useEffect(() => {
    setName(source.name);
    setDisplayName(source.display_name);
    setDescription(source.description);
    setTier(source.tier);
    setScoreType(source.score_type);
    setRubric(source.rubric);
    setDefaultWeight(String(source.default_weight));
    setActive(source.active);
    // Reset only when switching to a different metric — re-syncing on every
    // field change would clobber unsaved edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source.id]);

  const parsedWeight = Number.parseFloat(defaultWeight);
  const weightValid = Number.isFinite(parsedWeight) && parsedWeight >= 0;

  const isDirty =
    name !== source.name ||
    displayName !== source.display_name ||
    description !== source.description ||
    tier !== source.tier ||
    scoreType !== source.score_type ||
    rubric !== source.rubric ||
    (weightValid && parsedWeight !== source.default_weight) ||
    active !== source.active;

  const nameValid = isValidSnakeCase(name);
  const canSave = nameValid && weightValid && (source.id === null || isDirty) && !saving;

  const discard = () => {
    setName(source.name);
    setDisplayName(source.display_name);
    setDescription(source.description);
    setTier(source.tier);
    setScoreType(source.score_type);
    setRubric(source.rubric);
    setDefaultWeight(String(source.default_weight));
    setActive(source.active);
  };

  const handleSave = () => {
    if (!canSave) return;
    // Predefined metrics keep their internal `name` immutable on the backend,
    // so omit it from the patch to avoid a 409 even when the field is read-only.
    const patch: MetricUpdatePatch = {
      display_name: displayName,
      description,
      tier,
      score_type: scoreType,
      rubric,
      default_weight: parsedWeight,
      is_draft: !active,
    };
    if (!source.is_predefined) patch.name = name;
    onSave(patch, {
      ...source,
      name,
      display_name: displayName,
      description,
      tier,
      score_type: scoreType,
      rubric,
      default_weight: parsedWeight,
      active,
    });
  };

  return (
    <div className="flex flex-col h-full border-l border-border bg-background">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <TierBadge tier={tier} />
          <ScoreTypeBadge type={scoreType} />
          {source.is_predefined && (
            <span className="px-2 py-0.5 rounded text-[10px] uppercase tracking-wider border border-border/60 bg-accent/40 text-muted-foreground/80">
              Predefined
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isDirty && source.id !== null && (
            <Button
              size="sm"
              variant="ghost"
              className="text-muted-foreground hover:text-foreground"
              onClick={discard}
            >
              Discard
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            className={cn(
              'gap-2 transition-colors',
              saved && 'border-green-500/40 text-green-400'
            )}
            onClick={handleSave}
            disabled={!canSave}
          >
            {saved ? (
              <>
                <Check />
                Saved
              </>
            ) : source.id === null ? (
              'Create metric'
            ) : (
              'Save changes'
            )}
          </Button>
          {source.id !== null && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              title="Delete metric"
              type="button"
              className="h-9 w-9 p-0 text-muted-foreground/50 hover:text-red-400"
            >
              <Trash2 />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            type="button"
            className="h-9 w-9 p-0 text-muted-foreground/50 hover:text-foreground"
          >
            <X />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-5 py-4 space-y-5">
        <div className="flex items-center justify-between py-2 px-3 rounded-md border border-border bg-accent/20">
          <div>
            <p className="text-xs text-foreground">Active</p>
            <p className="text-[10px] text-muted-foreground/60 mt-0.5">
              {active
                ? 'This metric is included in eval runs.'
                : 'This metric is disabled globally and excluded from eval runs.'}
            </p>
          </div>
          <Switch
            checked={active}
            onCheckedChange={setActive}
            className="h-4 w-7 [&>span]:h-3 [&>span]:w-3 [&>span]:data-[state=checked]:translate-x-3 data-[state=checked]:bg-green-500/80"
          />
        </div>

        <div>
          <label className="block text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1.5">
            Display name
          </label>
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Tool Routing"
            className="h-8 text-xs bg-accent/40 border-border"
          />
        </div>

        <div>
          <label className="block text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1.5">
            Description
          </label>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="One-line summary of what this metric measures"
            className="h-8 text-xs bg-accent/40 border-border"
          />
        </div>

        <div>
          <label className="block text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1.5">
            Internal name <span className="normal-case">(snake_case)</span>
          </label>
          <Input
            value={name}
            onChange={(e) =>
              setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))
            }
            placeholder="e.g. tool_routing"
            disabled={source.is_predefined}
            className={cn(
              'h-8 text-xs font-mono bg-accent/40 border-border',
              name && !nameValid && 'border-red-500/50 focus-visible:ring-red-500/20',
              source.is_predefined && 'opacity-70 cursor-not-allowed'
            )}
          />
          {source.is_predefined ? (
            <p className="text-[10px] text-muted-foreground/50 mt-1">
              Predefined metrics share a stable id used by existing eval configs and
              cannot be renamed.
            </p>
          ) : name && !nameValid ? (
            <p className="text-[10px] text-red-400 mt-1">
              Must start with a letter and contain only lowercase letters, digits, and
              underscores.
            </p>
          ) : null}
        </div>

        <div>
          <label className="block text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1.5">
            Tier
          </label>
          <div className="grid grid-cols-2 gap-2">
            {TIERS.map((t) => {
              const m = TIER_META[t];
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTier(t)}
                  className={cn(
                    'flex flex-col items-start gap-0.5 px-3 py-2 rounded border text-left transition-colors',
                    tier === t
                      ? cn('border-border bg-accent/60', m.color.split(' ')[1])
                      : 'border-border bg-accent/20 text-muted-foreground hover:bg-accent/40'
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', m.dot)} />
                    <span className="text-xs">{m.label}</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground/60 leading-tight pl-3">
                    {m.description}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1.5">
            Score type
          </label>
          <div className="flex gap-2">
            {SCORE_TYPES.map((st) => {
              const m = SCORE_TYPE_META[st];
              const selected = scoreType === st;
              return (
                <button
                  key={st}
                  type="button"
                  onClick={() => setScoreType(st)}
                  className={cn(
                    'flex-1 px-3 py-2 rounded border text-xs transition-colors',
                    selected
                      ? 'border-border bg-accent/60 text-foreground'
                      : 'border-border bg-accent/20 text-muted-foreground hover:bg-accent/40'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={cn(
                        'w-3 h-3 rounded-full border-2 flex items-center justify-center shrink-0',
                        selected ? 'border-foreground' : 'border-muted-foreground/40'
                      )}
                    >
                      {selected && <div className="w-1.5 h-1.5 rounded-full bg-foreground" />}
                    </div>
                    <span>{m.label}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1.5">
            Default weight
          </label>
          <Input
            type="number"
            inputMode="decimal"
            step="0.05"
            min="0"
            value={defaultWeight}
            onChange={(e) => setDefaultWeight(e.target.value)}
            placeholder="e.g. 0.15"
            className={cn(
              'h-8 text-xs font-mono bg-accent/40 border-border',
              defaultWeight && !weightValid && 'border-red-500/50 focus-visible:ring-red-500/20'
            )}
          />
          <p
            className={cn(
              'text-[10px] mt-1',
              defaultWeight && !weightValid ? 'text-red-400' : 'text-muted-foreground/50'
            )}
          >
            {defaultWeight && !weightValid
              ? 'Must be a non-negative number.'
              : 'Relative weight applied when this metric is included in an eval — weights are renormalized to sum to 1.'}
          </p>
        </div>

        <div className="flex flex-col flex-1">
          <label className="block text-[10px] text-muted-foreground/60 uppercase tracking-wider mb-1.5">
            Rubric
          </label>
          <Textarea
            value={rubric}
            onChange={(e) => setRubric(e.target.value)}
            placeholder={
              scoreType === 'scored'
                ? `Measures: <one-sentence summary>.\n\n5: <criterion>\n   Example: ...\n4: ...\n...`
                : `Measures: <one-sentence summary>.\n\npass: <criterion>\n   Example: ...\n\nfail: <criterion>\n   Example: ...`
            }
            className="min-h-[320px] text-xs font-mono bg-accent/40 border-border resize-none leading-relaxed"
          />
          <p className="text-[10px] text-muted-foreground/40 mt-1.5">
            {scoreType === 'scored'
              ? 'Start with “Measures: …” then list levels 5 → 0, each with an Example: line.'
              : 'Start with “Measures: …” then define pass and fail criteria, each with an Example: line.'}
          </p>
        </div>
      </div>
    </div>
  );
}
