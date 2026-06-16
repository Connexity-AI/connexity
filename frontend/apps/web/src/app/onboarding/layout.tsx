import type { FC, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

const OnboardingLayout: FC<Props> = ({ children }) => (
  <div className="flex min-h-screen w-full flex-col items-center justify-center">
    <div className="w-full max-w-md px-4">{children}</div>
  </div>
);

export default OnboardingLayout;
