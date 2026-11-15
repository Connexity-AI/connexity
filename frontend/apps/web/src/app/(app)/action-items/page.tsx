import { ActionItemsView } from '@/components/action-items/action-items-view';
import ErrorBoundarySuspense from '@/components/common/error-boundary-suspense';
import { AgentsService, ClarificationsService } from '@/client/sdk.gen';

import type { FC } from 'react';

type SearchParams = Record<string, string | string[] | undefined>;

const PAGE = 5;

const one = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value)?.trim() || undefined;

/** How many to show: ``first``, then 5 more each time "N more" is pressed. */
const shown = (value: string | string[] | undefined, first = PAGE) =>
  Math.min(200, Math.max(first, Math.ceil((Number(one(value)) || first) / PAGE) * PAGE));

const ActionItems: FC<{ params: SearchParams }> = async ({ params }) => {
  const agentId = one(params.agent);
  // One agent's questions: 50 at first, then 5 more at a time.
  const openShown = shown(params.shown, agentId ? 50 : PAGE);
  const answeredShown = shown(params.answered);
  const parkedShown = shown(params.parked);
  const list = (state: 'open' | 'answered' | 'parked', limit: number, confident = false) =>
    ClarificationsService.listWorkspaceClarifications({
      query: {
        state,
        limit,
        this_week: state === 'answered',
        confident,
        ...(agentId ? { agent_id: agentId } : {}),
      },
    });
  const [open, confident, answered, parked, agents] = await Promise.all([
    list('open', openShown),
    // Every confident suggestion, for the batch panel, not only those on the page.
    list('open', 200, true),
    list('answered', answeredShown),
    list('parked', parkedShown),
    AgentsService.listWorkspaceAgents({ query: { period: '30d' } }),
  ]);
  if (!open.data || !confident.data || !answered.data || !parked.data) {
    throw new Error('Action items could not be loaded.');
  }

  return (
    <ActionItemsView
      open={open.data}
      confident={confident.data}
      answered={answered.data}
      parked={parked.data}
      agents={(agents.data?.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
      agentId={agentId}
      shown={{ open: openShown, answered: answeredShown, parked: parkedShown }}
    />
  );
};

interface Props {
  searchParams: Promise<SearchParams>;
}

/**
 * Action items (designs/screens/Connexity Action items.dc.html;
 * plans/2026-11-15-action-items.md): only clarifications, until other items exist.
 */
const ActionItemsPage: FC<Props> = async ({ searchParams }) => {
  const params = await searchParams;

  return (
    <ErrorBoundarySuspense fallback={null}>
      <ActionItems params={params} />
    </ErrorBoundarySuspense>
  );
};

export default ActionItemsPage;
