import { notFound } from 'next/navigation';

import { CallView } from '@/components/calls/call-view';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { CallsService } from '@/client/sdk.gen';

import type { FC } from 'react';

const Call: FC<{ id: string; startAt?: number }> = async ({ id, startAt }) => {
  const [screen, recording] = await Promise.all([
    CallsService.getCallScreen({ path: { call_id: id } }),
    CallsService.getCallRecording({ path: { call_id: id } }),
  ]);
  if (screen.response?.status === 404 || screen.response?.status === 422) notFound();
  if (!screen.data) throw new Error('The call could not be loaded.');

  return (
    <CallView call={screen.data} recordingUrl={recording.data?.url ?? null} startAt={startAt} />
  );
};

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/** A single call (designs/screens/Connexity Call.dc.html; plans/2026-11-13-single-call.md). */
const CallPage: FC<Props> = async ({ params, searchParams }) => {
  const { id } = await params;
  const raw = (await searchParams).t;
  const seconds = Number(Array.isArray(raw) ? raw[0] : raw);
  const startAt = Number.isFinite(seconds) && seconds >= 0 ? seconds : undefined;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <Call id={id} startAt={startAt} />
    </ErrorBoundarySuspense>
  );
};

export default CallPage;
