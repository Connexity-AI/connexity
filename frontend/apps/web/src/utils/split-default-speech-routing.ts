/** Split `provider/local_model` speech catalog ids into form fields. */
export function splitSpeechModelRoute(route: string): { provider: string; model: string } {
  const idx = route.indexOf('/');
  if (idx <= 0) {
    return { provider: '', model: route };
  }
  return {
    provider: route.slice(0, idx),
    model: route.slice(idx + 1),
  };
}
