import { splitSpeechModelRoute } from '@/utils/split-default-speech-routing';

import type { SpeechModelsPublic, VoicesPublic } from '@/client/types.gen';

export function speechSelectionFromCatalog(
  catalog: SpeechModelsPublic,
  existing?: { provider: string; model: string } | null
): { provider: string; model: string } {
  if (existing?.provider.trim() && existing.model.trim()) {
    return { provider: existing.provider.trim(), model: existing.model.trim() };
  }

  if (catalog.default_model) {
    const { provider, model } = splitSpeechModelRoute(catalog.default_model);
    if (provider && model) {
      return { provider, model };
    }
  }

  const first = catalog.data[0]?.models[0];
  if (first) {
    return { provider: first.provider, model: first.model };
  }

  return { provider: '', model: '' };
}

export function defaultVoiceIdFromCatalog(
  catalog: VoicesPublic,
  existingVoiceId?: string | null
): string {
  if (existingVoiceId?.trim()) {
    return existingVoiceId.trim();
  }
  if (catalog.default_voice_id?.trim()) {
    return catalog.default_voice_id.trim();
  }
  return catalog.data[0]?.id ?? '';
}
