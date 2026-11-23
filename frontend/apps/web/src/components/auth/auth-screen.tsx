import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';

import { Button } from '@workspace/ui/components/ui/button';

import type { FC, ReactNode } from 'react';

interface Props {
  title: string;
  /** The muted line under the title. */
  line: ReactNode;
  children: ReactNode;
}

/** A title, one muted line and what follows: the layout of the password reset screens. */
export const AuthScreen: FC<Props> = ({ title, line, children }) => (
  <div className="flex flex-col gap-6">
    <div className="flex flex-col gap-1">
      <h1 className="m-0 text-title font-medium text-ink">{title}</h1>
      <p className="m-0 text-pretty text-body text-ink-secondary">{line}</p>
    </div>
    {children}
  </div>
);

export const BackToSignIn: FC = () => (
  <span className="text-label text-ink-secondary">
    Back to{' '}
    <Link href={UrlGenerator.login()} className="font-medium text-ink underline">
      Sign in
    </Link>
  </span>
);

/** Expired, already used and unknown reset links all look like this. */
export const LinkNoLongerWorks: FC = () => (
  <AuthScreen
    title="This link no longer works"
    line="Reset links work once and expire after 1 hour."
  >
    <div className="pt-2">
      <Button asChild className="h-10 w-full">
        <Link href={UrlGenerator.forgotPassword()}>Send a new link</Link>
      </Button>
    </div>
    <BackToSignIn />
  </AuthScreen>
);

export default AuthScreen;
