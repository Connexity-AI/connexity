'use client';

import { useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { Calendar } from 'lucide-react';

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
// The design's columns without Score and Critical issues (rule 14).
const COLUMNS = 'grid-cols-[minmax(0,1fr)_104px_88px]';

/** "Retell · Conversational flow" */
export const subline = (agent: AgentListItemPublic) =>
  [agent.platform ? PLATFORMS[agent.platform] : null, agent.type ? TYPES[agent.type] : null]
    .filter(Boolean)
    .join(' · ');

/** "1.2 s", or a dash with no latency. */
export const seconds = (value: number | null | undefined) =>
  value == null ? '—' : `${value.toFixed(1)} s`;

/** "synced 5 minutes ago" */
const synced = (iso: string | null | undefined) => {
  if (!iso) return null;
  const minutes = Math.max(0, Math.round((Date.now() - parseTime(iso).getTime()) / 60000));
  if (minutes < 1) return 'synced just now';
  if (minutes < 60) return `synced ${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `synced ${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
  const days = Math.round(hours / 24);
  return `synced ${days} ${days === 1 ? 'day' : 'days'} ago`;
};

interface Props {
  agents: AgentListPublic;
}

/**
 * Agents (designs/screens/Connexity Agents.dc.html). A row opens the agent's page;
 * Score and Critical issues wait for their features (rule 14).
 */
export const AgentsView: FC<Props> = ({ agents }) => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const caption = synced(agents.synced_at);

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
          {caption && (
            <span className="whitespace-nowrap text-label text-ink-muted">Retell · {caption}</span>
          )}
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
          <span className="text-right">Latency</span>
          <span className="text-right">Calls</span>
        </div>
        {agents.data.map((agent) => (
          <Link
            key={agent.id}
            href={UrlGenerator.agent(agent.id)}
            className={cn(
              'grid min-h-16 items-center gap-4 border-t border-hairline px-6 py-2.5 text-body text-ink no-underline hover:bg-wash',
              COLUMNS
            )}
          >
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="flex min-w-0 items-center gap-2">
                <span className="truncate">{agent.name}</span>
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
            <span className="text-right">{seconds(agent.latency_seconds)}</span>
            <span className="text-right">{agent.calls.toLocaleString()}</span>
          </Link>
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
