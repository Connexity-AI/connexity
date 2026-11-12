import { CircleCheck, CircleDashed, OctagonAlert, TriangleAlert } from 'lucide-react';

import type { LucideIcon } from 'lucide-react';

/** The four states colour may mean. Each is always colour, icon and word together. */
export type Severity = 'critical' | 'warning' | 'passed' | 'unchecked';

export const SEVERITY: Record<Severity, { label: string; icon: LucideIcon; text: string }> = {
  critical: { label: 'Critical', icon: OctagonAlert, text: 'text-critical' },
  warning: { label: 'Warning', icon: TriangleAlert, text: 'text-warning' },
  passed: { label: 'Passed', icon: CircleCheck, text: 'text-passed' },
  unchecked: { label: 'Unchecked', icon: CircleDashed, text: 'text-unchecked' },
};
