import { getWebhookPayloadPreview } from '@/actions/environments';
import type { ErrorResponse } from '@/client/types.gen';
import { environmentKeys } from '@/constants/query-keys';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';

interface WebhookPayloadPreviewQueryArgs {
  agentId: string;
  environmentName: string;
  evalGateEvalConfigId: string | null;
}

export function webhookPayloadPreviewQuery({
  agentId,
  environmentName,
  evalGateEvalConfigId,
}: WebhookPayloadPreviewQueryArgs) {
  return {
    queryKey: environmentKeys.webhookPayloadPreview(
      agentId,
      environmentName,
      evalGateEvalConfigId
    ),
    queryFn: async () => {
      const result = await getWebhookPayloadPreview(
        agentId,
        environmentName,
        evalGateEvalConfigId
      );
      if (!isSuccessApiResult(result)) {
        if (isErrorApiResult<ErrorResponse>(result) && typeof result.error.detail === 'string') {
          throw new Error(result.error.detail);
        }
        throw new Error('Failed to fetch webhook payload preview');
      }
      return result.data;
    },
  };
}
