import { redirect } from 'next/navigation';

import DashboardTitle from '@/components/dashboard/common/dashboard-title';
import AlertProfile from '@/components/dashboard/settings/alert-profile';
import TabsUserSettings from '@/components/dashboard/settings/tabs-user-settings';
import { UsersService } from '@/client/sdk.gen';
import { ROUTES } from '@/constants/routes';

import type { FC } from 'react';

const { LOGIN } = ROUTES;

const SettingsPage: FC = async () => {
  // Note: no fetching in child components, no Suspense
  const result = await UsersService.readUserMe();
  const currentUser = result.data;

  if (!currentUser) redirect(LOGIN);

  return (
    <div className="space-y-6">
      <DashboardTitle
        title="User Settings"
        description="Manage your account settings and preferences."
        alert={<AlertProfile />}
      />
      <TabsUserSettings currentUser={currentUser} />
    </div>
  );
};

export default SettingsPage;
