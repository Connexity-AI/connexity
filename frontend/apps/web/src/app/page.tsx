'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { UsersService } from '@/client/sdk.gen';
import { EnvError } from '@/utils/error';
import { isNextBuild } from '@/utils/runtime';
import { waitMs } from '@/utils/wait';
import { DELAY } from '@/constants/delay';
import { ROUTES } from '@/constants/routes';
import { getPublicEnv } from '@/config/process-env';

import type { FC } from 'react';

const { LOGIN, DASHBOARD } = ROUTES;
const { HOME_PAGE_REDIRECT } = DELAY;

// Must be client component to show loader before redirect
// hey-api client doesn't work on client with cookies
// Todo: rethink this

const HomePage: FC = () => {
  const router = useRouter();

  const { SITE_URL, API_URL } = getPublicEnv();
  const isBuildPhase = isNextBuild();

  if (!isBuildPhase) {
    const requiredVars = { API_URL, SITE_URL };

    const missingVars = Object.keys(requiredVars).filter(
      (key) => !requiredVars[key as keyof typeof requiredVars]
    );

    if (missingVars.length > 0) {
      throw new EnvError(`Missing environment variables in frontend: ${missingVars.join(', ')}.`);
    }
  }

  useEffect(() => {
    const redirect = async () => {
      // client side client, without cookies
      const result = await UsersService.readUserMe();
      const currentUser = result.data;

      await waitMs(HOME_PAGE_REDIRECT);

      const redirectUrl = currentUser ? DASHBOARD : LOGIN;
      router.push(redirectUrl);
    };

    redirect();
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
        <p className="mt-2 text-gray-600">Redirecting...</p>
      </div>
    </div>
  );
};

export default HomePage;
