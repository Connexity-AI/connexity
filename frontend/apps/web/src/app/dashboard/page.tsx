import CardSmallSkeleton from '@workspace/ui/components/skeletons/card-small';
import ListSkeleton from '@workspace/ui/components/skeletons/list';

import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import DashboardTitle from '@/components/dashboard/common/dashboard-title';
import CardCurrentUser from '@/components/dashboard/home/card-current-user';
import CardSystemHealth from '@/components/dashboard/home/card-system-health';
import ListSystemStatus from '@/components/dashboard/home/list-system-status';
import { UsersService } from '@/client/sdk.gen';

import type { FC } from 'react';

const DashboardPage: FC = async () => {
  const result = await UsersService.readUserMe();
  const currentUser = result.data;

  const welcomeText = currentUser
    ? `Welcome back, ${currentUser.full_name ?? currentUser.email}!`
    : 'Welcome back!';

  return (
    <div className="space-y-6">
      <DashboardTitle
        title="Dashboard"
        description={`${welcomeText} Here's what's happening with your application.`}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <ErrorBoundarySuspense fallback={<CardSmallSkeleton />}>
          <CardCurrentUser />
        </ErrorBoundarySuspense>
        <ErrorBoundarySuspense fallback={<CardSmallSkeleton />}>
          <CardSystemHealth />
        </ErrorBoundarySuspense>
      </div>

      <ErrorBoundarySuspense fallback={<ListSkeleton count={3} />}>
        <ListSystemStatus />
      </ErrorBoundarySuspense>
    </div>
  );
};

export default DashboardPage;
