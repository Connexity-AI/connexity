/** Which tool names lack a runnable `platform_config.implementation`. */
export function missingLiveImplementations(agentTools: unknown[] | null | undefined): string[] {
  if (!agentTools?.length) {
    return [];
  }

  const missing: string[] = [];

  for (const raw of agentTools) {
    if (!raw || typeof raw !== 'object') continue;

    const t = raw as Record<string, unknown>;
    const fn = t.function;
    const name =
      typeof fn === 'object' &&
      fn !== null &&
      'name' in fn &&
      typeof (fn as { name: unknown }).name === 'string'
        ? (fn as { name: string }).name
        : null;

    if (!name) continue;

    const pc = t.platform_config;
    if (pc === null || pc === undefined || typeof pc !== 'object') {
      missing.push(name);
      continue;
    }

    const impl = (pc as { implementation?: unknown }).implementation;
    if (impl === null || impl === undefined) {
      missing.push(name);
    }
  }

  return missing;
}

export function platformAgentCanUseLiveTools(agentTools: unknown[] | null | undefined): boolean {
  return missingLiveImplementations(agentTools).length === 0;
}
