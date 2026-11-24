import Link from 'next/link';

import { UrlGenerator } from '@/common/url-generator/url-generator';
import { CircleCheck, CircleMinus } from 'lucide-react';

import { cn } from '@workspace/ui/lib/utils';

import type { MoneyPublic } from '@/client/types.gen';
import type { FC, ReactNode } from 'react';

const number = (n: number) => n.toLocaleString('en-US');
interface Props {
  money: MoneyPublic;
}

/**
 * The stripe at the top of the app when Connexity is paused for the agency
 * (designs/screens/Connexity Readiness Bar.dc.html): no subscription after the first
 * scan, the period's usage used up, or the subscription unpaid. Nothing otherwise.
 */
export const BillingStripe: FC<Props> = ({ money }) => {
  const billing = UrlGenerator.agency('billing');
  const link = (label: string) => (
    <Link href={billing} className="font-medium text-ink underline">
      {label}
    </Link>
  );
  let icon = <CircleMinus className="size-3.5 flex-none text-ink-secondary" aria-hidden />;
  let line: ReactNode;
  // While the balance is above zero a failed payment is a warning, not a pause.
  let warning = false;

  if (money.state === 'needs_subscription') {
    const scan = money.first_scan;
    const cut = scan && scan.of > scan.checked;
    icon = <CircleCheck className="size-3.5 flex-none text-ink-secondary" aria-hidden />;
    line = money.subscription_ended ? (
      <>
        <span className="font-medium">Your subscription has ended.</span>
        <span className="text-ink-secondary">
          {' '}
          Connexity is paused: new calls are not being checked and tests can’t run.
        </span>{' '}
        {link('Start subscription')}
      </>
    ) : (
      <>
        <span className="text-ink-secondary tabular-nums">
          {cut
            ? `Your first scan checked the latest ${number(scan.checked)} of ${number(scan.of)} calls.`
            : 'Your first scan is done.'}{' '}
          Start your subscription to keep checking new calls and run tests.
        </span>{' '}
        {link('Start subscription')}
      </>
    );
  } else if (money.state === 'out')
    line = (
      <>
        <span className="font-medium">You’ve used this month’s usage.</span>
        <span className="text-ink-secondary">
          {' '}
          Connexity is paused: new calls are not being checked and tests can’t run.
        </span>{' '}
        {link('Add funds')}
      </>
    );
  else if (money.state === 'unpaid')
    line = (
      <>
        <span className="font-medium">Your subscription is unpaid.</span>
        <span className="text-ink-secondary"> Connexity is paused.</span> {link('Update card')}
      </>
    );
  else if (money.payment_failed) {
    warning = true;
    line = (
      <>
        <span className="font-medium">A payment failed.</span>
        <span className="text-ink-secondary">
          {' '}
          Update your card before your balance runs out.
        </span>{' '}
        {link('Update card')}
      </>
    );
  } else return null;

  return (
    <div
      role="status"
      className={cn(
        'flex min-h-9 items-center gap-2.5 border-b border-hairline px-4 py-2 text-label text-ink',
        warning ? 'bg-warning-bg' : 'bg-wash'
      )}
    >
      {icon}
      <p className="m-0 min-w-0 flex-1 text-pretty">{line}</p>
    </div>
  );
};

export default BillingStripe;
