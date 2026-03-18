import { FC, ReactNode, Suspense } from 'react';

import ErrorBoundary from '@/components/common/error-boundary';

interface Props {
  children: ReactNode;
  fallback: ReactNode;
}

const ErrorBoundarySuspense: FC<Props> = ({ children, fallback }) => (
  <ErrorBoundary>
    {/* Suspense must be inside, ErrorBoundary is client component */}
    <Suspense fallback={fallback}>{children}</Suspense>
  </ErrorBoundary>
);

export default ErrorBoundarySuspense;
