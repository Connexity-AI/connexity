'use client';

import { useEffect, useMemo } from 'react';

import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCheck,
  FlaskConical,
  ListChecks,
  Target,
} from 'lucide-react';
import { useFormContext } from 'react-hook-form';

import { FormField, FormMessage } from '@workspace/ui/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@workspace/ui/components/ui/select';
import { cn } from '@workspace/ui/lib/utils';

import { evalConfigsListQuery } from '@/app/(app)/(agent)/_queries/eval-configs-list-query';
import type { AddEnvironmentFormValues } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import type { EvalConfigPublic } from '@/client/types.gen';

interface Props {
  agentId: string;
  disabled?: boolean;
}

export function EvalGateFormSection({ agentId, disabled = false }: Props) {
  const form = useFormContext<AddEnvironmentFormValues>();
  const { data, isLoading } = useQuery(evalConfigsListQuery(agentId));
  const configs: EvalConfigPublic[] = useMemo(
    () =>
      [...(data?.data ?? [])].sort((a, b) =>
        b.created_at.localeCompare(a.created_at)
      ),
    [data]
  );

  const enabled = form.watch('eval_gate_enabled');
  const selectedId = form.watch('eval_gate_eval_config_id');

  const selectedConfig = useMemo(
    () => (selectedId ? configs.find((c) => c.id === selectedId) ?? null : null),
    [configs, selectedId]
  );

  // If the selected config disappears (e.g. soft-deleted while modal is open), clear it.
  useEffect(() => {
    if (selectedId && !isLoading && !configs.some((c) => c.id === selectedId)) {
      form.setValue('eval_gate_eval_config_id', null);
    }
  }, [configs, isLoading, selectedId, form]);

  const handleToggle = () => {
    if (disabled) return;
    const next = !enabled;
    form.setValue('eval_gate_enabled', next, { shouldDirty: true });
    if (!next) {
      form.setValue('eval_gate_eval_config_id', null);
    }
  };

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <button
        type="button"
        onClick={handleToggle}
        disabled={disabled}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent/20 transition-colors disabled:opacity-60"
      >
        <div
          className={cn(
            'w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-all',
            enabled ? 'bg-foreground border-foreground' : 'border-border bg-transparent'
          )}
        >
          {enabled && <CheckCheck className="w-2.5 h-2.5 text-background" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <FlaskConical className="w-3.5 h-3.5 text-violet-400 shrink-0" />
            <span className="text-xs text-foreground">
              Require successful eval before deploy
            </span>
          </div>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Block deployments until the selected eval config passes its
            thresholds.
          </p>
        </div>
      </button>

      {enabled && (
        <div className="border-t border-border px-4 py-4 space-y-4 bg-accent/5">
          {configs.length === 0 ? (
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-border text-[11px] text-muted-foreground">
              <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
              No eval configs yet — create one in the Evals tab first.
            </div>
          ) : (
            <FormField
              control={form.control}
              name="eval_gate_eval_config_id"
              render={({ field }) => (
                <div className="space-y-1.5">
                  <label className="text-xs text-muted-foreground">Eval config</label>
                  <Select
                    value={field.value ?? undefined}
                    onValueChange={(v) => field.onChange(v)}
                    disabled={disabled}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue placeholder="Select an eval config…" />
                    </SelectTrigger>
                    <SelectContent>
                      {configs.map((c) => (
                        <SelectItem key={c.id} value={c.id} className="text-xs">
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </div>
              )}
            />
          )}

          {selectedConfig && (
            <div className="rounded-lg border border-border overflow-hidden">
              <div className="grid grid-cols-3">
                <Stat label="Test cases" value={selectedConfig.test_case_count ?? 0} />
                <Stat label="Total runs" value={selectedConfig.total_runs ?? 0} />
                <Stat
                  label="Effective"
                  value={selectedConfig.effective_test_case_count ?? 0}
                />
              </div>
              <div className="grid grid-cols-2 border-t border-border">
                <Threshold
                  icon={<ListChecks className="w-3 h-3 text-emerald-400" />}
                  label="Cases pass rate"
                  value={selectedConfig.config?.cases_pass_threshold ?? 100}
                  color="text-emerald-400"
                />
                <Threshold
                  icon={<Target className="w-3 h-3 text-violet-400" />}
                  label="Metrics pass rate"
                  value={selectedConfig.config?.metrics_pass_threshold ?? 80}
                  color="text-violet-400"
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="px-3 py-2.5 text-center border-r border-border last:border-r-0">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
        {label}
      </p>
      <p className="text-sm font-mono tabular-nums text-foreground mt-0.5">{value}</p>
    </div>
  );
}

function Threshold({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="px-3 py-2.5 border-r border-border last:border-r-0">
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p className={cn('text-sm font-mono tabular-nums mt-0.5', color)}>{value}%</p>
    </div>
  );
}
