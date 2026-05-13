'use client';

import { FormMessage } from '@workspace/ui/components/ui/form';

import { isPresentUserFacingFormMessage } from '@/app/(app)/(agent)/_components/evals/create-eval/is-present-user-facing-form-message';

interface SubmittedCustomUrlFieldFormMessageProps {
  isSubmitted: boolean;
  message: unknown;
}

export function SubmittedCustomUrlFieldFormMessage({
  isSubmitted,
  message,
}: SubmittedCustomUrlFieldFormMessageProps) {
  if (!isSubmitted) {
    return null;
  }

  if (!isPresentUserFacingFormMessage(message)) {
    return null;
  }

  return <FormMessage>{message}</FormMessage>;
}
