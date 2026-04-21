'use client';

import { useMemo } from 'react';

import type { EvalConfigPublic, RunPublic } from '@/client/types.gen';

interface UseEvalRunsDerivationsParams {
  runs: RunPublic[];
  configs: EvalConfigPublic[];
}

export function useEvalRunsDerivations({ runs, configs }: UseEvalRunsDerivationsParams) {
  const configById = useMemo(() => {
    const map = new Map<string, EvalConfigPublic>();
    for (const c of configs) map.set(c.id, c);
    return map;
  }, [configs]);

  const versions = useMemo(() => {
    const set = new Set<number>();
    for (const r of runs) {
      if (r.agent_version !== null && r.agent_version !== undefined) {
        set.add(r.agent_version);
      }
    }
    return Array.from(set).sort((a, b) => b - a);
  }, [runs]);

  const latestVersion = versions.length > 0 ? (versions[0] ?? null) : null;

  // Within each config: oldest = 1, newest = N. Used to show "#N" on duplicates.
  const repeatIndexByRun = useMemo(() => {
    const runsByConfig = new Map<string, RunPublic[]>();
    for (const r of runs) {
      const list = runsByConfig.get(r.eval_config_id) ?? [];
      list.push(r);
      runsByConfig.set(r.eval_config_id, list);
    }
    const map = new Map<string, number>();
    for (const list of runsByConfig.values()) {
      if (list.length <= 1) continue;
      const ascending = [...list].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
      ascending.forEach((r, i) => {
        map.set(r.id, i + 1);
      });
    }
    return map;
  }, [runs]);

  return { configById, versions, latestVersion, repeatIndexByRun };
}
