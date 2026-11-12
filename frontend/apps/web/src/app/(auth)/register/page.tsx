import FormRegister from '@/components/auth/form-register';

import type { FC } from 'react';

const RegisterPage: FC = () => (
  <div className="flex flex-col gap-6">
    <div className="flex flex-col gap-2 text-center">
      <h1 className="text-title font-medium">Create an account</h1>
      <p className="text-sm text-muted-foreground">Enter your details to get started</p>
    </div>

    <FormRegister />
  </div>
);

export default RegisterPage;
