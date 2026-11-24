'use server';

import { BillingService } from '@/client/sdk.gen';
import { getApiErrorMessage } from '@/utils/error';

import type { AutoTopUpUpdate } from '@/client/types.gen';

export type BillingLinkResult = { ok: true; url: string } | { ok: false; message: string };
export type BillingChangeResult = { ok: true } | { ok: false; message: string };

/** The address of Stripe's page that starts the subscription. */
export const startSubscriptionAction = async (agencyId: string): Promise<BillingLinkResult> => {
  const { data, error } = await BillingService.startSubscription({
    path: { agency_id: agencyId },
  });
  return data ? { ok: true, url: data.url } : { ok: false, message: getApiErrorMessage(error) };
};

/** The address of Stripe's page for the card and billing details. */
export const openPortalAction = async (agencyId: string): Promise<BillingLinkResult> => {
  const { data, error } = await BillingService.openPortal({ path: { agency_id: agencyId } });
  return data ? { ok: true, url: data.url } : { ok: false, message: getApiErrorMessage(error) };
};

export const cancelSubscriptionAction = async (agencyId: string): Promise<BillingChangeResult> => {
  const { data, error } = await BillingService.cancelSubscription({
    path: { agency_id: agencyId },
  });
  return data ? { ok: true } : { ok: false, message: getApiErrorMessage(error) };
};

export const resumeSubscriptionAction = async (agencyId: string): Promise<BillingChangeResult> => {
  const { data, error } = await BillingService.resumeSubscription({
    path: { agency_id: agencyId },
  });
  return data ? { ok: true } : { ok: false, message: getApiErrorMessage(error) };
};

/** The address of Stripe's page that adds funds to the balance. */
export const startTopUpAction = async (
  agencyId: string,
  amountUsd: number
): Promise<BillingLinkResult> => {
  const { data, error } = await BillingService.startTopUp({
    path: { agency_id: agencyId },
    body: { amount_usd: amountUsd },
  });
  return data ? { ok: true, url: data.url } : { ok: false, message: getApiErrorMessage(error) };
};

export const setAutoTopUpAction = async (
  agencyId: string,
  body: AutoTopUpUpdate
): Promise<BillingChangeResult> => {
  const { data, error } = await BillingService.setAutoTopUp({
    path: { agency_id: agencyId },
    body,
  });
  return data ? { ok: true } : { ok: false, message: getApiErrorMessage(error) };
};
