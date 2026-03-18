import Link from 'next/link';

import { Bird } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { ROUTES } from '@/constants/routes';

import type { FC } from 'react';

const { HOME } = ROUTES;

const NotFound: FC = () => (
  <div className="min-h-screen w-full flex-1 flex flex-col justify-center items-center">
    <div className="space-y-4 text-center">
      <div className="flex justify-center">
        <Bird className="size-24 text-muted-foreground" />
      </div>

      <h1 className="text-3xl font-extrabold tracking-tight">404 - Page Not Found</h1>
      <p className="text-muted-foreground">Oops! The page you are looking for does not exist.</p>

      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Button asChild variant="outline">
          <Link href={HOME}>Return to Home</Link>
        </Button>
      </div>
    </div>
  </div>
);

export default NotFound;
