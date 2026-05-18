import { Bot, FlaskConical } from 'lucide-react';

import { TextRuntimeKind } from '@/client/types.gen';

import type { CreateEvalRuntime } from '@/app/(app)/(agent)/_components/evals/create-eval/create-eval-form-schema';
import type { TextRuntimeKind as TextRuntimeKindType } from '@/client/types.gen';

export function runtimeConfigForKind(
  kind: TextRuntimeKindType,
  url: string = ''
): CreateEvalRuntime {
  if (kind === TextRuntimeKind.CUSTOM_ENDPOINT) {
    return { kind, url };
  }

  return { kind };
}

export function runtimeIconForKind(kind: TextRuntimeKindType) {
  if (kind === TextRuntimeKind.CONNEXITY) {
    return FlaskConical;
  }

  return Bot;
}
