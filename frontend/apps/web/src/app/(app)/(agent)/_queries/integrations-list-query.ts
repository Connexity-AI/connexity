import { listIntegrations } from '@/actions/integrations';
import { integrationKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export function integrationsListQuery() {
  return {
    queryKey: integrationKeys.list(),
    queryFn: async () => {
      const result = await listIntegrations();
      if (!isSuccessApiResult(result)) throw new Error('Failed to fetch integrations');
      return result.data;
    },
  };
}
