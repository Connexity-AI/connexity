import { getAppConfig } from '@/actions/config';
import { appConfigKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

export const appConfigQueries = {
  root: {
    queryKey: appConfigKeys.root(),
    queryFn: async () => {
      const result = await getAppConfig();
      if (!isSuccessApiResult(result)) {
        throw new Error('Failed to fetch app config');
      }
      return result.data;
    },
    staleTime: 5 * 60 * 1000,
  },
};
