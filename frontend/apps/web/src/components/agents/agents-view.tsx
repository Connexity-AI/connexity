'use client';

import { useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Calendar, OctagonAlert } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import { parseTime } from '@/components/calls/format';
import { Picker } from '@/components/common/picker';

import type { AgentListItemPublic, AgentListPublic } from '@/client/types.gen';
import type { FC } from 'react';

const PERIOD_LABELS: Record<string, string> = {
  '7d': 'Last 7 days',
  '30d': 'Last 30 days',
  '90d': 'Last 90 days',
};
export const PLATFORMS: Record<string, string> = {
  retell: 'Retell',
  vapi: 'Vapi',
  elevenlabs: 'ElevenLabs',
};
export const TYPES: Record<string, string> = {
  single_prompt: 'Single prompt',
  conversational_flow: 'Conversational flow',
};
// Agent, Version, Score, Critical issues, Latency p50/p95, Calls (as in the design).
const COLUMNS = 'grid-cols-[minmax(0,1fr)_72px_80px_128px_160px_88px]';

/** "Retell · Conversational flow" */
export const subline = (agent: AgentListItemPublic) =>
  [agent.platform ? PLATFORMS[agent.platform] : null, agent.type ? TYPES[agent.type] : null]
    .filter(Boolean)
    .join(' · ');

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "Since 6 Nov", in the viewer's time zone. */
const sinceLabel = (iso: string | null | undefined) => {
  if (!iso) return undefined;
  const date = parseTime(iso);
  return `Since ${date.getDate()} ${MONTHS[date.getMonth()]}`;
};

/** "0.8s/1.7s": p50, then p95 muted; a dash without a reply in the period. */
export const LatencyPair: FC<{
  p50: number | null | undefined;
  p95: number | null | undefined;
}> = ({ p50, p95 }) =>
  p50 == null || p95 == null ? (
    <span className="text-ink-muted">—</span>
  ) : (
    <span className="inline-flex items-baseline whitespace-nowrap">
      <span>{p50.toFixed(1)}s</span>
      <span className="text-ink-secondary">/{p95.toFixed(1)}s</span>
    </span>
  );

interface Props {
  agents: AgentListPublic;
}

/**
 * Agents (designs/screens/Connexity Agents.dc.html), lowest score first. A row opens the
 * agent's page; its critical count is its own link to that agent's critical issues,
 * laid over the row's link rather than inside it.
 */
export const AgentsView: FC<Props> = ({ agents }) => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();

  const pickPeriod = (value: string | undefined) => {
    const next = new URLSearchParams(params.toString());
    if (value && value !== '30d') next.set('period', value);
    else next.delete('period');
    const search = next.toString();
    startTransition(() => router.replace(search ? `${pathname}?${search}` : pathname));
  };

  return (
    <div className={cn('flex max-w-[1120px] flex-col gap-6', pending && 'opacity-70')}>
      <div className="flex min-h-10 items-center justify-between gap-4">
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="m-0 text-title font-medium">Agents</h1>
        </div>
        <Picker
          label="Last 30 days"
          value={agents.period}
          options={Object.entries(PERIOD_LABELS).map(([value, label]) => ({ value, label }))}
          onPick={pickPeriod}
          icon={<Calendar className="size-4 text-ink-secondary" aria-hidden />}
          align="end"
          clearable={false}
        />
      </div>

      <section className="overflow-hidden rounded-xl border border-hairline bg-surface-1">
        <div
          className={cn('grid h-10 items-center gap-4 px-6 text-label text-ink-secondary', COLUMNS)}
        >
          <span>Agent</span>
          <span>Version</span>
          <span className="text-right">Score</span>
          <span className="text-right">Critical issues</span>
          <span className="text-right">Latency p50/p95</span>
          <span className="text-right">Calls</span>
        </div>
        {agents.data.map((agent) => (
          <div
            key={agent.id}
            className={cn(
              'relative grid min-h-16 items-center gap-4 border-t border-hairline px-6 py-2.5 text-body text-ink hover:bg-wash',
              COLUMNS
            )}
          >
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="flex min-w-0 items-center gap-2">
                <Link
                  href={UrlGenerator.agent(agent.id)}
                  className="truncate text-ink no-underline after:absolute after:inset-0"
                >
                  {agent.name}
                </Link>
                {agent.spec === 'none' && (
                  <span className="inline-flex h-5 flex-none items-center rounded-md border border-hairline px-1.5 text-label text-ink-muted">
                    No spec
                  </span>
                )}
              </span>
              {subline(agent) && (
                <span className="text-label text-ink-muted">{subline(agent)}</span>
              )}
            </div>
            <span title={sinceLabel(agent.live_since)} className="relative text-ink-muted">
              {agent.live_version ? `v${agent.live_version}` : '—'}
            </span>
            <span className="text-right">
              {agent.score != null ? (
                <span className="font-medium">{agent.score}</span>
              ) : (
                <span className="text-ink-muted">—</span>
              )}
            </span>
            <span className="text-right">
              <Link
                href={UrlGenerator.criticalIssues(agent.id, agents.period)}
                title="Open critical issues of this agent"
                className={cn(
                  'relative inline-flex items-center gap-1.5 no-underline hover:underline',
                  agent.critical_issues ? 'text-critical' : 'text-ink-muted'
                )}
              >
                {agent.critical_issues ? <OctagonAlert className="size-3.5" aria-hidden /> : null}
                {(agent.critical_issues ?? 0).toLocaleString()}
              </Link>
            </span>
            <span className="text-right">
              <LatencyPair p50={agent.latency_p50} p95={agent.latency_p95} />
            </span>
            <span className="text-right">{agent.calls.toLocaleString()}</span>
          </div>
        ))}
        {agents.data.length === 0 && (
          <div className="border-t border-hairline px-6 py-5 text-ink-secondary">
            No agents yet. Your assistant adds them during setup.
          </div>
        )}
      </section>
    </div>
  );
};
