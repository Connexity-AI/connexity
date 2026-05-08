import type { AddEnvironmentFormValues } from '@/app/(app)/(agent)/agents/[agentId]/deploy/_components/add-environment-form-schema';
import { Platform } from '@/client/types.gen';

export type IntegrationPlatform = Extract<
  AddEnvironmentFormValues['platform'],
  typeof Platform.RETELL | typeof Platform.VAPI | typeof Platform.ELEVENLABS
>;

export function isIntegrationPlatform(
  platform: AddEnvironmentFormValues['platform']
): platform is IntegrationPlatform {
  return (
    platform === Platform.RETELL ||
    platform === Platform.VAPI ||
    platform === Platform.ELEVENLABS
  );
}

export function getIntegrationEmptyLabel(platform: IntegrationPlatform): string {
  if (platform === Platform.VAPI) {
    return 'No Vapi integrations found';
  }
  if (platform === Platform.ELEVENLABS) {
    return 'No ElevenLabs integrations found';
  }
  return 'No Retell integrations found';
}

export function getAgentLabel(platform: IntegrationPlatform): string {
  if (platform === Platform.VAPI) {
    return 'Assistant';
  }
  return 'Agent';
}
