import DashboardTitle from '@/components/dashboard/common/dashboard-title';

import type { FC } from 'react';

const DashboardPage: FC = () => {
  return (
    <div className="space-y-6">
      <DashboardTitle title="Dashboard" description="" />
    </div>
  );
};

export default DashboardPage;
