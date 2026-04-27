import { listIntegrations } from '@/actions/integrations';
import { isSuccessApiResult } from '@/utils/api';

import { IntegrationsClient } from '@/app/(app)/integrations/_components/integrations-client';

import type { IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';

const IntegrationsPage: FC = async () => {
  const result = await listIntegrations();
  const integrations: IntegrationPublic[] = isSuccessApiResult(result)
    ? result.data.data
    : [];

  return <IntegrationsClient initialData={integrations} />;
};

export default IntegrationsPage;
