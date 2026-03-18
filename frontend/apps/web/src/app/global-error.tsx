'use client';

import Link from 'next/link';

import { RefreshCcw, Settings } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { ENV_ERROR_TYPE } from '@/constants/error';
import { ROUTES } from '@/constants/routes';

import type { FC } from 'react';

import '@workspace/ui/global.css';

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

const { HOME } = ROUTES;

// Todo: improve design

// Note: global-error.tsx, global-not-found.tsx define own html and body tags, and need to import global.css from UI package

const GlobalError: FC<Props> = ({ error, reset }) => (
  <html>
    <body className="relative min-h-screen min-w-80 flex flex-col bg-background font-sans antialiased">
      <main className="flex-1 flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-md space-y-4 text-center">
          <div className="flex justify-center">
            <Settings className="size-24 text-muted-foreground" />
          </div>

          <h1 className="text-3xl font-extrabold tracking-tight">500 - Server Error</h1>
          <p className="text-muted-foreground">
            We are sorry, but something went wrong on our end. Please try again later.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button onClick={() => reset()} variant="outline">
              <RefreshCcw className="mr-2 size-4" /> Try Again
            </Button>
            <Button asChild>
              <Link href={HOME}>Return to Home</Link>
            </Button>
          </div>

          <AlertEnv error={error} />

          {error.digest && (
            <p className="text-sm text-muted-foreground">Error ID: {error.digest}</p>
          )}
        </div>
      </main>
    </body>
  </html>
);

interface AlertEnvProps {
  error: Error & { digest?: string };
}

const AlertEnv: FC<AlertEnvProps> = ({ error }) => {
  const isEnvError = (error as any)?.type === ENV_ERROR_TYPE;

  if (!isEnvError) return null;

  const infoText = 'See the full list of environment variables on this link:';
  const docsUrl = `https://github.com/space-step/connexity-evals/blob/main/README.md`;

  const consoleMessage = `${error.message} ${infoText} ${docsUrl}`;
  console.error(consoleMessage);

  return (
    <div>
      <p className="font-bold text-red-500 bg-gray-100 rounded p-2">{error.message}</p>
      <p className="text-muted-foreground mt-2">
        <span className="mr-2">{infoText}</span>
        <Link
          target="_blank"
          className="text-teal-600 hover:text-teal-700 hover:underline"
          href={docsUrl}
        >
          Environment variables
        </Link>
      </p>
    </div>
  );
};

export default GlobalError;
