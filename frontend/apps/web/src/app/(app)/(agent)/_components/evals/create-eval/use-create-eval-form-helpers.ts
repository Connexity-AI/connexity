import type {
  CreateEvalTestCaseValue,
} from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { MetricDefinition, TestCasePublic } from '@/client/types.gen';

export function buildMetricRows(
  metrics: MetricDefinition[],
  existing?: { metric: string; weight?: number | null }[] | null
) {
  if (existing && existing.length > 0) {
    const overrides = new Map(existing.map((m) => [m.metric, m.weight ?? null]));
    return metrics.map((def) => {
      const enabled = overrides.has(def.name);
      const overrideWeight = overrides.get(def.name);
      return {
        metric: def.name,
        enabled,
        weight: overrideWeight ?? def.default_weight,
      };
    });
  }
  return metrics.map((def) => ({
    metric: def.name,
    enabled: def.include_in_defaults !== false,
    weight: def.default_weight,
  }));
}

export function buildTestCaseRows(
  testCases: TestCasePublic[],
  rowsSpec: { test_case_id: string; repetitions: number }[]
): CreateEvalTestCaseValue[] {
  const byId = new Map(testCases.map((tc) => [tc.id, tc]));
  const rows: CreateEvalTestCaseValue[] = [];
  for (const spec of rowsSpec) {
    const tc = byId.get(spec.test_case_id);
    if (!tc) continue;
    rows.push({
      test_case_id: tc.id,
      name: tc.name,
      difficulty: tc.difficulty ?? null,
      tags: tc.tags ?? [],
      repetitions: spec.repetitions,
    });
  }
  return rows;
}
