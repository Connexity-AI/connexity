'use client';

import { useState } from 'react';
import Link from 'next/link';

import { ChevronDown, ChevronRight } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import type { AgencyUsagePublic, MoneyPublic } from '@/client/types.gen';
import type { FC } from 'react';

const CARD = 'rounded-xl border border-hairline bg-surface-1';
const GRID = 'md:grid md:grid-cols-[minmax(0,1fr)_128px_160px_104px] md:items-center md:gap-4';

const usd = (n: number) =>
  `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const count = (n: number) => n.toLocaleString('en-US');
const day = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
/** "5 days", "about 3 weeks". */
const lasts = (days: number) =>
  days < 14 ? `${days} ${days === 1 ? 'day' : 'days'}` : `about ${Math.round(days / 7)} weeks`;
const USED: Record<string, string> = {
  this: 'used this period',
  last: 'used last period',
  '30d': 'used in the last 30 days',
};

interface Props {
  agencyId: string;
  /** What the agency has left; absent when it could not be read. */
  money: MoneyPublic | null;
  usage: AgencyUsagePublic;
}

/**
 * The balance and usage part of Agency settings › Billing
 * (designs/screens/Connexity Billing.dc.html, "Balance and usage"). Everything is
 * counted by when Connexity recorded it, in the subscription's periods, so "this
 * period" is what came off the included amount and the balance. Dollars are at list
 * price; Connexity's own costs are never shown.
 */
export const BillingUsage: FC<Props> = ({ agencyId, money, usage }) => {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const hasPeriod = money !== null && money.period_end !== null && money.included_usd > 0;
  const scan = money?.first_scan ?? null;
  const total = usage.cost_usd;
  const shown = usage.parts.filter((p) => p.cost_usd > 0);
  const price = (meter: string) => usage.parts.find((p) => p.meter === meter)?.unit_price_usd;
  const csv = `/api/client-proxy/api/v1/agencies/${agencyId}/billing/usage.csv?period=${usage.period.key}`;

  return (
    <>
      {money && (
        <div className={cn(CARD, 'flex flex-col gap-3 px-6 py-5')}>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {hasPeriod && (
              <div className="flex flex-col gap-1.5">
                <span className="text-label text-ink-secondary">Included this period</span>
                <span className="text-ink tabular-nums">
                  <span className="text-title font-medium">{usd(money.included_left_usd)}</span> of
                  ${count(money.included_usd)} left
                </span>
                <span
                  aria-hidden
                  className="block h-1 overflow-hidden rounded-full bg-unchecked-bg"
                >
                  <span
                    className="block h-full rounded-full bg-ink-secondary"
                    style={{
                      width: `${Math.min(100, (100 * money.included_left_usd) / money.included_usd)}%`,
                    }}
                  />
                </span>
                {money.period_end && (
                  <span className="text-label text-ink-muted tabular-nums">
                    Resets {day(money.period_end)}
                  </span>
                )}
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <span className="text-label text-ink-secondary">Balance</span>
              <span
                className={cn(
                  'text-title font-medium tabular-nums',
                  money.state === 'out' ? 'text-critical' : 'text-ink'
                )}
              >
                {usd(money.balance_usd)}
              </span>
              <span className="text-label text-ink-muted">
                Used after your included amount. Never expires.
              </span>
            </div>
          </div>
          {money.days_left !== null && money.days_left !== undefined && (
            <span className="text-label text-ink-secondary tabular-nums">
              Lasts {lasts(money.days_left)} at your current rate
            </span>
          )}
          {scan && scan.checked > 0 && (
            <span className="text-label text-ink-muted tabular-nums">
              Your first scan is included:{' '}
              {scan.of > scan.checked
                ? `the latest ${count(scan.checked)} calls of ${count(scan.of)} checked`
                : `${count(scan.checked)} calls checked`}
            </span>
          )}
        </div>
      )}

      <div className={cn(CARD, 'flex flex-col gap-4 px-6 py-5')}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-0.5">
            <span className="text-tile font-medium text-ink tabular-nums">{usd(total)}</span>
            <span className="text-label text-ink-secondary tabular-nums">
              {USED[usage.period.key] ?? 'used'} · {day(usage.period.starts_at)} to{' '}
              {day(usage.period.ends_at)}
            </span>
          </div>
          {usage.periods.length > 1 && (
            <nav aria-label="Period" className="flex rounded-md border border-border-control p-0.5">
              {usage.periods.map((period) => (
                <Link
                  key={period.key}
                  href={`?section=billing&period=${period.key}`}
                  scroll={false}
                  aria-current={period.key === usage.period.key ? 'page' : undefined}
                  className={cn(
                    'flex h-[26px] items-center rounded-sm px-2.5 text-label no-underline',
                    period.key === usage.period.key
                      ? 'bg-wash font-medium text-ink'
                      : 'text-ink-secondary'
                  )}
                >
                  {period.label}
                </Link>
              ))}
            </nav>
          )}
        </div>
        {total > 0 ? (
          <>
            <span aria-hidden className="flex h-1.5 gap-0.5 overflow-hidden rounded-full">
              {shown.map((part, index) => (
                <span
                  key={part.meter}
                  className={cn('block h-full', index === 0 ? 'bg-ink' : 'bg-ink-muted')}
                  style={{ width: `${(100 * part.cost_usd) / total}%` }}
                />
              ))}
            </span>
            <ul className="m-0 flex list-none flex-wrap gap-x-6 gap-y-1 p-0 text-label text-ink-secondary">
              {shown.map((part, index) => (
                <li key={part.meter} className="flex items-center gap-2 tabular-nums">
                  <span
                    aria-hidden
                    className={cn('size-2 rounded-full', index === 0 ? 'bg-ink' : 'bg-ink-muted')}
                  />
                  {part.label}: {count(part.quantity)} {part.unit} · {usd(part.cost_usd)}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <span className="text-ink-secondary">No usage yet</span>
        )}
      </div>

      {usage.workspaces.length > 0 && (
        <div className={CARD}>
          <div className="flex h-12 items-center justify-between gap-3 pr-4 pl-6">
            <span className="font-medium text-ink">By workspace</span>
            <a
              href={csv}
              download
              className="text-label text-ink-secondary underline hover:text-ink"
            >
              Download CSV
            </a>
          </div>
          <div
            className={cn(
              GRID,
              'hidden h-9 border-t border-hairline px-6 text-label text-ink-secondary md:grid'
            )}
          >
            <span>Workspace</span>
            <span className="text-right">Calls observed</span>
            <span className="text-right">Simulated messages</span>
            <span className="text-right">Cost</span>
          </div>
          {usage.workspaces.map((workspace) => {
            const isOpen = open[workspace.id] ?? false;
            const Chevron = isOpen ? ChevronDown : ChevronRight;
            return (
              <div key={workspace.id} className="border-t border-hairline">
                <button
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => setOpen((o) => ({ ...o, [workspace.id]: !isOpen }))}
                  className={cn(
                    GRID,
                    'flex w-full cursor-pointer items-center justify-between gap-3 border-0 bg-transparent px-6 py-3 text-left text-body text-ink hover:bg-wash md:min-h-12 md:py-0'
                  )}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <Chevron className="size-3.5 flex-none text-ink-muted" aria-hidden />
                    <span className="truncate">{workspace.name}</span>
                    {workspace.deleted && (
                      <span className="flex h-5 flex-none items-center rounded-sm border border-hairline px-1.5 text-label text-ink-secondary">
                        Deleted
                      </span>
                    )}
                  </span>
                  <span className="hidden text-right text-ink-secondary tabular-nums md:block">
                    {count(workspace.observed_minutes)} min
                  </span>
                  <span className="hidden text-right text-ink-secondary tabular-nums md:block">
                    {count(workspace.simulated_messages)}
                  </span>
                  <span className="flex-none text-right tabular-nums">
                    {usd(workspace.cost_usd)}
                  </span>
                </button>
                {isOpen &&
                  workspace.agents.map((agent) => (
                    <div
                      key={agent.id}
                      className={cn(
                        GRID,
                        'flex items-center justify-between gap-3 px-6 py-2 text-label text-ink-secondary md:min-h-9 md:py-0'
                      )}
                    >
                      <span className="min-w-0 truncate pl-[22px]">{agent.name}</span>
                      <span className="hidden text-right tabular-nums md:block">
                        {count(agent.observed_minutes)} min
                      </span>
                      <span className="hidden text-right tabular-nums md:block">
                        {count(agent.simulated_messages)}
                      </span>
                      <span className="flex-none text-right tabular-nums">
                        {usd(agent.cost_usd)}
                      </span>
                    </div>
                  ))}
              </div>
            );
          })}
          <div
            className={cn(
              GRID,
              'flex items-center justify-between gap-3 border-t border-hairline px-6 py-3 font-medium text-ink md:min-h-12 md:py-0'
            )}
          >
            <span>Total</span>
            <span className="hidden text-right tabular-nums md:block">
              {count(usage.workspaces.reduce((n, w) => n + w.observed_minutes, 0))} min
            </span>
            <span className="hidden text-right tabular-nums md:block">
              {count(usage.workspaces.reduce((n, w) => n + w.simulated_messages, 0))}
            </span>
            <span className="text-right tabular-nums">{usd(total)}</span>
          </div>
        </div>
      )}

      {usage.movers.length > 0 && (
        <div className={cn(CARD, 'flex flex-col gap-2 px-6 py-4')}>
          <span className="text-label text-ink-secondary">What moved it most</span>
          {usage.movers.map((mover, index) => (
            <span
              // Two runs on one agent on one day share a label; the order is fixed.
              key={index}
              className="flex flex-wrap justify-between gap-x-4 text-ink tabular-nums"
            >
              <span>{mover.label}</span>
              <span className="text-ink-secondary">
                {count(mover.quantity)} {mover.unit} · {usd(mover.cost_usd)}
              </span>
            </span>
          ))}
        </div>
      )}

      <div className={cn(CARD, 'flex flex-col gap-2 px-6 py-4 text-label')}>
        <span className="text-ink-secondary">How it’s priced</span>
        <dl className="m-0 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-[160px_minmax(0,1fr)]">
          <dt className="text-ink-secondary">Subscription</dt>
          <dd className="m-0 text-ink tabular-nums">$299 a month, includes $299 of usage</dd>
          <dt className="text-ink-secondary">Real call observed</dt>
          <dd className="m-0 text-ink tabular-nums">
            ${(price('observed_minutes') ?? 0.03).toFixed(2)} per minute, rounded up per call
          </dd>
          <dt className="text-ink-secondary">Text simulation</dt>
          <dd className="m-0 text-ink tabular-nums">
            ${(price('simulated_caller_messages') ?? 0.02).toFixed(2)} per simulated caller message,
            judging included
          </dd>
        </dl>
        <span className="text-pretty text-ink-muted">
          Your voice platform bills the agent’s own replies in tests on your account with them.
        </span>
      </div>
    </>
  );
};

export default BillingUsage;
