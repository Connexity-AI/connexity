import { redirect } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import FormLlmKeyOnboarding from '@/components/onboarding/form-llm-key-onboarding';
import { UsersService } from '@/client/sdk.gen';

import type { FC } from 'react';

const OnboardingPage: FC = async () => {
  // Bounce authenticated users with a key away from onboarding.
  try {
    const status = await UsersService.readOnboardingStatus();
    if (status.data?.onboarding_complete) {
      redirect(UrlGenerator.dashboard());
    }
  } catch {
    // Not authenticated → push to login.
    redirect(UrlGenerator.login());
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Add an LLM API key</h1>
        <p className="text-sm text-muted-foreground">
          We use your API key for test case generation and eval judging. Your key is encrypted
          at rest and never shared.
        </p>
      </div>

      <FormLlmKeyOnboarding />
    </div>
  );
};

export default OnboardingPage;
