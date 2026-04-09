import FormLogin from '@/components/auth/form-login';

import type { FC } from 'react';

const LoginPage: FC = () => (
  <div className="flex flex-col gap-6">
    <div className="flex flex-col gap-2 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
      <p className="text-sm text-muted-foreground">Enter your credentials to sign in</p>
    </div>

    <FormLogin />
  </div>
);

export default LoginPage;
