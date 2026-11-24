'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';

import {
  cancelSubscriptionAction,
  openPortalAction,
  resumeSubscriptionAction,
  startSubscriptionAction,
} from '@/actions/billing';

import type { BillingChangeResult, BillingLinkResult } from '@/actions/billing';
import type { BillingPublic } from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

const CARD = 'rounded-xl border border-hairline bg-surface-1';
const QUIET =
  'cursor-pointer border-0 bg-transparent p-0 text-label text-ink-secondary underline hover:text-ink disabled:cursor-default disabled:opacity-60';

const day = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
const brand = (name: string) => name.charAt(0).toUpperCase() + name.slice(1);
const two = (n: number) => String(n).padStart(2, '0');

interface Props {
  agencyId: string;
  billing: BillingPublic;
  /** The person has just come back from Stripe's payment page. */
  justPaid: boolean;
}

/**
 * Agency settings › Billing (designs/screens/Connexity Billing.dc.html): the
 * subscription, the card and the billing details. Paying and every card field are on
 * Stripe's pages; this screen links to them. The balance, usage, top-ups and invoices
 * of the design are not built yet and are not shown.
 */
export const BillingView: FC<Props> = ({ agencyId, billing, justPaid }) => {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [failure, setFailure] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const { subscription, card, details } = billing;
  const { state, price_usd: price, included_usd: included } = subscription;
  const until = subscription.period_end ? day(subscription.period_end) : null;
  const running = state === 'active' || state === 'past_due' || state === 'unpaid';
  const hasCustomer = running || state === 'ended' || card !== null || details !== null;

  const leave = (action: () => Promise<BillingLinkResult>) => {
    setFailure(null);
    startTransition(async () => {
      const result = await action();
      if (!result.ok) return setFailure(result.message);
      window.location.assign(result.url);
    });
  };
  const change = (action: () => Promise<BillingChangeResult>, after?: () => void) => {
    setFailure(null);
    startTransition(async () => {
      const result = await action();
      if (!result.ok) return setFailure(result.message);
      after?.();
      router.refresh();
    });
  };
  const toPortal = () => leave(() => openPortalAction(agencyId));

  let subscriptionCard: ReactNode;
  if (!running)
    subscriptionCard = (
      <div className={`${CARD} flex flex-wrap items-center justify-between gap-4 px-6 py-5`}>
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-ink">Start your subscription</span>
          <span className="text-label text-ink-secondary tabular-nums">
            ${price} a month, includes ${included} of usage
          </span>
        </div>
        <Button
          disabled={isPending}
          onClick={() => leave(() => startSubscriptionAction(agencyId))}
          className="h-9 px-3.5"
        >
          Start subscription
        </Button>
      </div>
    );
  else if (subscription.ends_at_period_end)
    subscriptionCard = (
      <div className={`${CARD} flex flex-wrap items-center justify-between gap-4 px-6 py-5`}>
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-ink tabular-nums">Connexity · ${price} a month</span>
          <span suppressHydrationWarning className="text-label text-ink-secondary tabular-nums">
            Active until {until}
          </span>
        </div>
        <button
          type="button"
          disabled={isPending}
          onClick={() => change(() => resumeSubscriptionAction(agencyId))}
          className={QUIET}
        >
          Resume subscription
        </button>
      </div>
    );
  else
    subscriptionCard = (
      <div className={`${CARD} flex flex-wrap items-center justify-between gap-4 px-6 py-5`}>
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-ink tabular-nums">Connexity · ${price} a month</span>
          {state === 'active' && (
            <span suppressHydrationWarning className="text-label text-ink-secondary tabular-nums">
              Includes ${included} of usage{until ? ` · Renews ${until}` : ''}
            </span>
          )}
          {state === 'past_due' && (
            <span role="alert" className="text-label text-critical">
              A renewal payment failed and is being tried again. Update your card.
            </span>
          )}
          {state === 'unpaid' && (
            <span role="alert" className="text-label text-critical">
              Your subscription is unpaid. Update your card.
            </span>
          )}
        </div>
        <button
          type="button"
          disabled={isPending}
          onClick={() => setCancelling(true)}
          className={QUIET}
        >
          Cancel subscription
        </button>
      </div>
    );

  return (
    <div className="flex min-w-0 flex-col gap-4">
      {justPaid && (
        <span role="status" className="text-label text-ink-secondary">
          {state === 'active'
            ? 'Your subscription has started.'
            : 'Your payment is processing. This page updates when it’s done.'}
        </span>
      )}
      {subscriptionCard}

      {hasCustomer && (
        <div className={CARD}>
          <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4">
            <div className="flex flex-col gap-0.5">
              <span className="text-label text-ink-secondary">Payment method</span>
              <span className="text-ink tabular-nums">
                {card
                  ? `${brand(card.brand)} ending ${card.last4} · expires ${two(card.exp_month)}/${two(card.exp_year % 100)}`
                  : 'No card on file'}
              </span>
            </div>
            <button type="button" disabled={isPending} onClick={toPortal} className={QUIET}>
              {card ? 'Change' : 'Add card'}
            </button>
          </div>
          <div className="flex flex-wrap items-start justify-between gap-3 border-t border-hairline px-6 py-4">
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="text-label text-ink-secondary">Billing details</span>
              {details && (details.name || details.address.length > 0) ? (
                <>
                  {details.name && <span className="text-ink">{details.name}</span>}
                  {details.address.map((line) => (
                    <span key={line} className="text-label text-ink-secondary">
                      {line}
                    </span>
                  ))}
                  {details.tax_ids.map((id) => (
                    <span key={id} className="text-label text-ink-secondary tabular-nums">
                      Tax ID {id}
                    </span>
                  ))}
                </>
              ) : (
                <span className="text-ink">No billing details yet</span>
              )}
            </div>
            <button type="button" disabled={isPending} onClick={toPortal} className={QUIET}>
              Edit
            </button>
          </div>
          <div className="border-t border-hairline px-6 pt-3 pb-4 text-label text-pretty text-ink-muted">
            Card and billing details are entered on our payment provider’s page, never in Connexity.
          </div>
        </div>
      )}

      {!billing.read_from_stripe && (
        <span className="text-label text-ink-muted">
          Payment details can’t be shown right now. Try again in a minute.
        </span>
      )}
      {failure && (
        <span role="alert" className="text-label text-critical">
          {failure}
        </span>
      )}

      <Dialog open={cancelling} onOpenChange={setCancelling}>
        <DialogContent>
          <DialogTitle>Cancel your subscription?</DialogTitle>
          <DialogDescription suppressHydrationWarning className="text-body text-ink-secondary">
            {until
              ? `Your subscription stays active until ${until} and is not renewed. You can resume it before then.`
              : 'Your subscription is not renewed. You can resume it before it ends.'}
          </DialogDescription>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={isPending}
              onClick={() =>
                change(
                  () => cancelSubscriptionAction(agencyId),
                  () => setCancelling(false)
                )
              }
              className="px-3.5 text-critical"
            >
              Cancel subscription
            </Button>
            <DialogClose asChild>
              <Button type="button" className="px-3.5">
                Keep subscription
              </Button>
            </DialogClose>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BillingView;
