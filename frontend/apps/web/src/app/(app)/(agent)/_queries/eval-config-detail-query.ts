import { getEvalConfig, listEvalConfigMembers } from '@/actions/eval-configs';
import { isSuccessApiResult } from '@/utils/api';
import { evalConfigKeys } from '@/constants/query-keys';

import type { EvalConfigMemberPublic, EvalConfigPublic } from '@/client/types.gen';

export interface EvalConfigDetail {
  config: EvalConfigPublic;
  members: EvalConfigMemberPublic[];
}

export function evalConfigDetailQuery(evalConfigId: string) {
  return {
    queryKey: evalConfigKeys.detail(evalConfigId),

    queryFn: async (): Promise<EvalConfigDetail> => {
      const [configResult, membersResult] = await Promise.all([
        getEvalConfig(evalConfigId),
        listEvalConfigMembers(evalConfigId),
      ]);

      if (!isSuccessApiResult(configResult)) throw new Error('Failed to fetch eval config');

      if (!isSuccessApiResult(membersResult)) {
        throw new Error('Failed to fetch eval config members');
      }

      return { config: configResult.data, members: membersResult.data.data };
    },
    staleTime: 30 * 1000,
  };
}
