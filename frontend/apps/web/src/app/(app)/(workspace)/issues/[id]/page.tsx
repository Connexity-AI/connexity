import { notFound } from 'next/navigation';

import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { IssueView } from '@/components/issues/issue-view';
import { IssuesService } from '@/client/sdk.gen';

import type { FC } from 'react';

const Issue: FC<{ id: string }> = async ({ id }) => {
  const response = await IssuesService.getIssue({ path: { issue_id: id } });
  if (response.response?.status === 404 || response.response?.status === 422) notFound();
  if (!response.data) throw new Error('The issue could not be loaded.');

  return <IssueView issue={response.data} />;
};

interface Props {
  params: Promise<{ id: string }>;
}

/** One issue (designs/screens/Connexity Issue.dc.html; plans/2026-11-13-issue-page.md). */
const IssuePage: FC<Props> = async ({ params }) => {
  const { id } = await params;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <Issue id={id} />
    </ErrorBoundarySuspense>
  );
};

export default IssuePage;
