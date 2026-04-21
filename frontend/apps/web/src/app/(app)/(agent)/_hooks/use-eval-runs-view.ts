'use client';

import { useMemo, useState } from 'react';

import type { EvalConfigPublic, RunPublic } from '@/client/types.gen';

export interface RunConfigGroup {
  configId: string;
  configName: string;
  items: RunPublic[];
}

interface UseEvalRunsViewParams {
  runs: RunPublic[];
  configById: Map<string, EvalConfigPublic>;
}

export function useEvalRunsView({ runs, configById }: UseEvalRunsViewParams) {
  const [versionFilter, setVersionFilter] = useState<number | null>(null);
  const [groupByConfig, setGroupByConfig] = useState(false);

  const filteredRuns = useMemo(() => {
    if (versionFilter === null) return runs;
    return runs.filter((r) => r.agent_version === versionFilter);
  }, [runs, versionFilter]);

  const sortedRuns = useMemo(() => {
    const sorted = [...filteredRuns];
    sorted.sort((a, b) => {
      if (groupByConfig && a.eval_config_id !== b.eval_config_id) {
        const aName = configById.get(a.eval_config_id)?.name ?? a.eval_config_id;
        const bName = configById.get(b.eval_config_id)?.name ?? b.eval_config_id;
        return aName.localeCompare(bName);
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return sorted;
  }, [filteredRuns, groupByConfig, configById]);

  const groupedRuns = useMemo<RunConfigGroup[] | null>(() => {
    if (!groupByConfig) return null;
    return groupRunsByConfig(sortedRuns, configById);
  }, [groupByConfig, sortedRuns, configById]);

  return {
    versionFilter,
    setVersionFilter,
    groupByConfig,
    setGroupByConfig,
    sortedRuns,
    groupedRuns,
  };
}

function groupRunsByConfig(
  runs: RunPublic[],
  configById: Map<string, EvalConfigPublic>
): RunConfigGroup[] {
  const groups = new Map<string, RunPublic[]>();
  for (const r of runs) {
    const list = groups.get(r.eval_config_id) ?? [];
    list.push(r);
    groups.set(r.eval_config_id, list);
  }
  const result: RunConfigGroup[] = [];
  for (const [configId, items] of groups) {
    result.push({
      configId,
      configName: configById.get(configId)?.name ?? 'Unknown config',
      items,
    });
  }
  return result;
}
