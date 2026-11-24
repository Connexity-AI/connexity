'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { Download } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import { cn } from '@workspace/ui/lib/utils';

import { setAutoTopUpAction, startTopUpAction } from '@/actions/billing';

import type { AutoTopUpPublic, InvoicePublic, MoneyPublic } from '@/client/types.gen';
import type { FC } from 'react';

const CARD = 'rounded-xl border border-hairline bg-surface-1';
const TILES = [100, 500, 2000];
const MIN = 50;
const MAX = 10000;
const SHOWN = 5;
const FIELD =
  'h-8 w-20 rounded-md border border-border-control bg-surface-0 px-2 text-right text-body text-ink tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-border-control';

const usd = (n: number) =>
  `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const day = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
const lasts = (days: number) =>
  days < 14 ? `${days} ${days === 1 ? 'day' : 'days'}` : `${Math.round(days / 7)} weeks`;
const STATUS: Record<string, string> = {
  paid: 'Paid',
  processing: 'Processing',
  failed: 'Failed',
};

interface AddFundsProps {
  agencyId: string;
  /** What is left, to say how long an amount would last. */
  money: MoneyPublic | null;
}

/** "Add funds" and its dialog: an amount, then Stripe's page. */
export const AddFunds: FC<AddFundsProps> = ({ agencyId, money }) => {
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState<number | null>(500);
  const [other, setOther] = useState('');
  const [failure, setFailure] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const typed = Number(other);
  const amount = picked ?? (Number.isInteger(typed) ? typed : 0);
  const tooLittle = picked === null && other !== '' && amount < MIN;
  const valid = amount >= MIN && amount <= MAX;
  // The rate of the last days, from what is left and how long it lasts.
  const left = money ? money.included_left_usd + money.balance_usd : 0;
  const days = money?.days_left;
  const about = valid && days && left > 0 ? Math.floor(amount / (left / days)) : null;

  const pay = () => {
    setFailure(null);
    startTransition(async () => {
      const result = await startTopUpAction(agencyId, amount);
      if (!result.ok) return setFailure(result.message);
      window.location.assign(result.url);
    });
  };

  return (
    <>
      <Button onClick={() => setOpen(true)} className="h-9 px-3.5">
        Add funds
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogTitle>Add funds</DialogTitle>
          <DialogDescription className="sr-only">
            Choose an amount to add to your balance.
          </DialogDescription>
          <div role="radiogroup" aria-label="Amount" className="grid grid-cols-3 gap-2">
            {TILES.map((tile) => (
              <button
                key={tile}
                type="button"
                role="radio"
                aria-checked={picked === tile}
                onClick={() => {
                  setPicked(tile);
                  setOther('');
                }}
                className={cn(
                  'h-11 cursor-pointer rounded-md border bg-transparent text-body text-ink tabular-nums',
                  picked === tile ? 'border-ink font-medium' : 'border-border-control'
                )}
              >
                ${tile.toLocaleString('en-US')}
              </button>
            ))}
          </div>
          <label className="flex flex-col gap-1.5 text-label text-ink-secondary">
            Other amount
            <span className="flex items-center gap-1.5 text-ink">
              $
              <input
                inputMode="numeric"
                value={other}
                onChange={(e) => {
                  setOther(e.target.value.replace(/[^0-9]/g, ''));
                  setPicked(null);
                }}
                aria-invalid={tooLittle || undefined}
                className={cn(FIELD, 'w-32 text-left', tooLittle && 'border-critical')}
              />
            </span>
            {tooLittle && (
              <span role="alert" className="text-critical">
                The minimum is $50.
              </span>
            )}
          </label>
          <div className="flex flex-col gap-1 text-label text-pretty text-ink-muted">
            {about !== null && about > 0 && (
              <span className="text-ink-secondary">About {lasts(about)} at your current rate</span>
            )}
            <span>Plus tax where it applies. Added funds never expire and are non-refundable.</span>
          </div>
          {failure && (
            <span role="alert" className="text-label text-critical">
              {failure}
            </span>
          )}
          <div className="flex justify-end gap-2">
            <DialogClose asChild>
              <Button type="button" variant="secondary" className="px-3.5">
                Cancel
              </Button>
            </DialogClose>
            <Button type="button" disabled={!valid || isPending} onClick={pay} className="px-3.5">
              Continue to payment
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

interface AutoTopUpProps {
  agencyId: string;
  setting: AutoTopUpPublic;
  hasCard: boolean;
  /** Opens Stripe's page to add a card, when the switch is turned on without one. */
  onNeedsCard: () => void;
}

/** The auto top-up card: a switch and one sentence with its amount. */
export const AutoTopUp: FC<AutoTopUpProps> = ({ agencyId, setting, hasCard, onNeedsCard }) => {
  const router = useRouter();
  const [amount, setAmount] = useState(String(setting.amount_usd));
  const [failure, setFailure] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const save = (enabled: boolean) => {
    const body = { enabled, amount_usd: Number(amount) || 0 };
    if (body.amount_usd < MIN) return setFailure('The amount to add is at least $50.');
    if (body.amount_usd > MAX) return setFailure('The amount to add is at most $10,000.');
    setFailure(null);
    startTransition(async () => {
      const result = await setAutoTopUpAction(agencyId, body);
      if (!result.ok) return setFailure(result.message);
      router.refresh();
    });
  };
  const toggle = () => {
    if (!setting.enabled && !hasCard) return onNeedsCard();
    save(!setting.enabled);
  };
  const changed = Number(amount) !== setting.amount_usd;
  const digits = (set: (value: string) => void) => (e: { target: { value: string } }) =>
    set(e.target.value.replace(/[^0-9]/g, ''));

  return (
    <div className={cn(CARD, 'flex flex-col gap-3 px-6 py-5')}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-ink">Auto top-up</span>
          <span className="text-label text-pretty text-ink-secondary">
            Keeps Connexity running by adding funds before your balance runs out.
          </span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={setting.enabled}
          aria-label="Auto top-up"
          disabled={isPending}
          onClick={toggle}
          className={cn(
            'relative h-6 w-10 flex-none cursor-pointer rounded-full border-0 p-0 transition-colors',
            setting.enabled ? 'bg-ink' : 'bg-unchecked-bg'
          )}
        >
          <span
            aria-hidden
            className={cn(
              'absolute top-0.5 block size-5 rounded-full bg-surface-0 transition-all',
              setting.enabled ? 'left-[18px]' : 'left-0.5'
            )}
          />
        </button>
      </div>
      {setting.enabled ? (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-2 text-ink">
          When your included usage and balance run out, add $
          <input
            inputMode="numeric"
            aria-label="Amount to add, in dollars"
            value={amount}
            onChange={digits(setAmount)}
            className={FIELD}
          />
          .
          {changed && (
            <Button
              variant="secondary"
              disabled={isPending}
              onClick={() => save(true)}
              className="h-8 px-3"
            >
              Save
            </Button>
          )}
        </div>
      ) : (
        <span className="text-label text-ink-muted">
          Without it, Connexity pauses when your balance reaches $0.
        </span>
      )}
      {failure && (
        <span role="alert" className="text-label text-critical">
          {failure}
        </span>
      )}
    </div>
  );
};

/** Invoices, newest first: five, then all. */
export const Invoices: FC<{ invoices: InvoicePublic[] }> = ({ invoices }) => {
  const [all, setAll] = useState(false);
  const shown = all ? invoices : invoices.slice(0, SHOWN);
  const grid =
    'grid grid-cols-[minmax(0,1fr)_auto_32px] items-center gap-4 md:grid-cols-[120px_minmax(0,1fr)_104px_96px_32px]';

  return (
    <div className={CARD}>
      <div className="flex h-12 items-center px-6 font-medium text-ink">Invoices</div>
      {invoices.length === 0 ? (
        <div className="border-t border-hairline px-6 py-4 text-ink-secondary">
          No invoices yet.
        </div>
      ) : (
        <>
          <div
            className={cn(
              grid,
              'hidden h-9 border-t border-hairline px-6 text-label text-ink-secondary md:grid'
            )}
          >
            <span>Date</span>
            <span>Description</span>
            <span className="text-right">Amount</span>
            <span>Status</span>
            <span />
          </div>
          {shown.map((invoice) => (
            <div
              key={invoice.id}
              className={cn(grid, 'min-h-12 border-t border-hairline px-6 py-2 text-ink')}
            >
              <span className="text-label text-ink-secondary tabular-nums md:text-body">
                {day(invoice.created_at)}
              </span>
              <span className="hidden md:block">{invoice.description}</span>
              <span className="text-right tabular-nums">{usd(invoice.amount_usd)}</span>
              <span
                className={cn(
                  'hidden text-label md:block',
                  invoice.status === 'failed' ? 'text-critical' : 'text-ink-secondary'
                )}
              >
                {STATUS[invoice.status] ?? invoice.status}
              </span>
              {invoice.url ? (
                <a
                  href={invoice.url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Download the invoice of ${day(invoice.created_at)}`}
                  className="flex size-8 items-center justify-center rounded-md text-ink-muted hover:bg-wash hover:text-ink"
                >
                  <Download className="size-4" aria-hidden />
                </a>
              ) : (
                <span />
              )}
            </div>
          ))}
          {!all && invoices.length > SHOWN && (
            <div className="border-t border-hairline px-6 py-3">
              <button
                type="button"
                onClick={() => setAll(true)}
                className="cursor-pointer border-0 bg-transparent p-0 text-label text-ink-secondary underline hover:text-ink"
              >
                Show all
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
