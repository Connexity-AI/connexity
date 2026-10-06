import type { EnvironmentPublic } from '@/client/types.gen';
import { Platform } from '@/client/types.gen';

interface AgentWithOptionalPlatform {
  platform?: Platform | null;
}

export function subtitlePlatformForAddEnvironmentDialog(
  environment: EnvironmentPublic | null,
  agent: AgentWithOptionalPlatform | undefined | null
): Platform | null {
  if (environment !== null) {
    return null;
  }

  const platform = agent?.platform;
  if (platform === undefined || platform === null) {
    return null;
  }

  if (platform === Platform.WEBHOOK) {
    return null;
  }

  return platform;
}
