import { Brand } from '@/components/common/brand';

import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

/** Sign in and create an account (designs/screens/Connexity Sign in.dc.html). */
const AuthLayout: FC<Props> = ({ children }) => (
  <div className="min-h-screen w-full bg-surface-0 px-4">
    <main className="mx-auto flex w-full max-w-[360px] flex-col gap-8 pt-24 pb-12">
      <Brand />
      {children}
    </main>
  </div>
);

export default AuthLayout;
