import { Platform } from '@/client/types.gen';

export function platformLabel(platform: Platform): string {
  if (platform === Platform.WEBHOOK) return 'Custom';
  if (platform === Platform.RETELL) return 'Retell';
  if (platform === Platform.VAPI) return 'Vapi';
  if (platform === Platform.ELEVENLABS) return 'ElevenLabs';
  return platform;
}

export function platformBadgeClassName(platform: Platform): string {
  if (platform === Platform.WEBHOOK) {
    return 'text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 uppercase tracking-wide';
  }
  if (platform === Platform.VAPI) {
    return 'text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 uppercase tracking-wide';
  }
  if (platform === Platform.ELEVENLABS) {
    return 'text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 uppercase tracking-wide';
  }
  return 'text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 uppercase tracking-wide';
}
