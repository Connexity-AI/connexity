import { WorkService } from '@/client/sdk.gen';

import type { WorkPublic } from '@/client/types.gen';

/** Work polls `/work` while open and visible (roadmap 10.195; Dmytro, 2026-11-19). */
export const WORK_POLL_MS = 10_000;

export const WORK_KEY = ['work'] as const;

/** The sidebar's waiting count: seeded from the layout, then written by each Work reload,
 * so it follows Work without a request of its own. */
export const WORK_WAITING_KEY = ['work', 'waiting'] as const;

/** Work's list, counts and done line; the same query on the server and in the browser. */
export const workQuery = () => ({
  queryKey: WORK_KEY,
  queryFn: async (): Promise<WorkPublic> => {
    const result = await WorkService.readWork();
    if (!result.data) throw new Error('Work could not be loaded.');
    return result.data;
  },
  // Fresh for half a tick: the server's copy is not fetched again on first load.
  staleTime: WORK_POLL_MS / 2,
});
