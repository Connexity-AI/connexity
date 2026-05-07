import { getWebhookPayloadPreview } from '@/actions/environments';
import { environmentKeys } from '@/constants/query-keys';
import { isSuccessApiResult } from '@/utils/api';

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
        throw new Error('Failed to fetch webhook payload preview');
      }
      return result.data;
    },
  };
}
