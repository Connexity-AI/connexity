/**
 * Which tool names lack a runnable `platform_config.implementation`.
 *
 * Mirrors backend `validate_live_tool_snapshot`: tools flagged
 * `platform_config.terminating` (e.g. predefined `end_call` / `transfer_call`)
 * end the simulation loop without executing an implementation, so they're
 * skipped here.
 */
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

    if ('terminating' in pc && pc.terminating === true) continue;

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
