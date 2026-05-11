import { Bot, FlaskConical } from 'lucide-react';

import { EvaluationEngineKind } from '@/client/types.gen';

import type { CreateEvalEvaluationEngine } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { EvaluationEngineKind as EvaluationEngineKindType } from '@/client/types.gen';

export function engineConfigForKind(
  kind: EvaluationEngineKindType,
  url: string = ''
): CreateEvalEvaluationEngine {
  if (kind === EvaluationEngineKind.CUSTOM_URL) {
    return { kind, url };
  }

  return { kind };
}

export function engineIconForKind(kind: EvaluationEngineKindType) {
  if (kind === EvaluationEngineKind.CONNEXITY) {
    return FlaskConical;
  }

  return Bot;
}
