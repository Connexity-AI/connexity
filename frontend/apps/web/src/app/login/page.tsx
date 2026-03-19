import { Card, CardContent, CardHeader } from '@workspace/ui/components/ui/card';

import ButtonGithubLogin from '@/components/auth/button-github-login';
import FormLogin from '@/components/auth/form-login';

import type { FC } from 'react';

const LoginPage: FC = () => (
  <div className="min-h-screen flex flex-col items-center justify-center bg-linear-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
    {/* Card */}
    <Card className="w-full max-w-md shadow-xl border-0 bg-white/80 backdrop-blur-sm dark:bg-slate-900/80">
      <CardHeader className="flex-row items-center justify-center mb-6">
        <span className="text-2xl font-bold">Sign In</span>
      </CardHeader>
      <CardContent className="space-y-8">
        <ButtonGithubLogin />
        <FormLogin />
      </CardContent>
    </Card>
  </div>
);

export default LoginPage;
