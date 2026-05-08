import { getWebhookPayloadPreview } from '@/actions/environments';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { environmentKeys } from '@/constants/query-keys';

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
        const error = isErrorApiResult(result) ? result.error : null;
        if (typeof error === 'object' && error !== null && 'detail' in error) {
          const detail = error.detail;
          if (typeof detail === 'string') {
            throw new Error(detail);
          }
        }
        throw new Error('Failed to fetch webhook payload preview');
      }
      return result.data;
    },
  };
}
