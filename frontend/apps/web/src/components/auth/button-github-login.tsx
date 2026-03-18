import Link from 'next/link';

import IconsCustom from '@workspace/ui/components/icons-custom';
import { Button } from '@workspace/ui/components/ui/button';
import { cn } from '@workspace/ui/lib/utils';

import { ROUTES } from '@/constants/routes';
import { getPublicEnv } from '@/config/process-env';

import type { FC } from 'react';

interface Props {
  className?: string;
}

const { GitHub } = IconsCustom;

const { LOGIN_GITHUB } = ROUTES.API;

const ButtonGithubLogin: FC<Props> = async ({ className }) => {
  const { API_URL } = getPublicEnv();

  // Note: BROWSER (<a/> or <Link />) must call this API url, not http client or server
  const absoluteApiUrl = `${API_URL}${LOGIN_GITHUB}`;

  return (
    <Button
      asChild
      className={cn(
        'w-full h-12 flex items-center justify-center gap-2 rounded-md font-medium text-white bg-green-600 hover:bg-green-700 active:bg-green-800 transition-colors',
        className
      )}
    >
      <Link href={absoluteApiUrl}>
        <GitHub className="w-5 h-5" />
        Sign in with GitHub
      </Link>
    </Button>
  );
};

export default ButtonGithubLogin;
