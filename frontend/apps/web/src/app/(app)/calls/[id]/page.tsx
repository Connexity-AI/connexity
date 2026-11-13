import { notFound } from 'next/navigation';

import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { CallView } from '@/components/calls/call-view';
import { CallsService } from '@/client/sdk.gen';

import type { FC } from 'react';

const Call: FC<{ id: string }> = async ({ id }) => {
  const [screen, recording] = await Promise.all([
    CallsService.getCallScreen({ path: { call_id: id } }),
    CallsService.getCallRecording({ path: { call_id: id } }),
  ]);
  if (screen.response?.status === 404 || screen.response?.status === 422) notFound();
  if (!screen.data) throw new Error('The call could not be loaded.');

  return <CallView call={screen.data} recordingUrl={recording.data?.url ?? null} />;
};

interface Props {
  params: Promise<{ id: string }>;
}

/** A single call (designs/screens/Connexity Call.dc.html; plans/2026-11-13-single-call.md). */
const CallPage: FC<Props> = async ({ params }) => {
  const { id } = await params;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <Call id={id} />
    </ErrorBoundarySuspense>
  );
};

export default CallPage;
