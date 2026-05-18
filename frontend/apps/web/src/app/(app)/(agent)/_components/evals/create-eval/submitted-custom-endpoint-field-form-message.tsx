'use client';

import { FormMessage } from '@workspace/ui/components/ui/form';

import { isPresentUserFacingFormMessage } from '@/app/(app)/(agent)/_components/evals/create-eval/runtime-test-status-message';

interface SubmittedCustomEndpointFieldFormMessageProps {
  isSubmitted: boolean;
  message: unknown;
}

export function SubmittedCustomEndpointFieldFormMessage({
  isSubmitted,
  message,
}: SubmittedCustomEndpointFieldFormMessageProps) {
  if (!isSubmitted) {
    return null;
  }

  if (!isPresentUserFacingFormMessage(message)) {
    return null;
  }

  return <FormMessage>{message}</FormMessage>;
}
