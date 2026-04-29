---
name: tanstack-streaming
description: TanStack Query streaming with Next.js App Router - server prefetching, dehydration, Suspense boundaries, useSuspenseQuery/useSuspenseInfiniteQuery hydration pattern. Use when implementing data fetching that streams from server to client using TanStack React Query with Next.js RSC.
user-invocable: true
---

# TanStack Query Streaming with Next.js App Router

This skill describes our pattern for streaming server-prefetched data to client components using TanStack Query + React Suspense in Next.js App Router.

## Architecture Overview

```
SERVER (RSC page.tsx)
  ├─ getQueryClient() — singleton per request
  ├─ prefetchQuery / prefetchInfiniteQuery (with or without await)
  ├─ dehydrate(queryClient) — serializes cache including pending queries
  └─ <HydrateProvider state={dehydratedState}> — passes cache to client

CLIENT (components wrapped in Suspense)
  ├─ useSuspenseQuery() / useSuspenseInfiniteQuery() — reads hydrated cache
  ├─ If data is already resolved → renders immediately
  └─ If data is still pending (streamed) → Suspense boundary shows fallback
```

## Key Files in This Codebase

- **getQueryClient**: `@/lib/react-query/getQueryClient` — singleton pattern, server creates fresh per request, client reuses single instance
- **HydrateProvider**: `@/app/_common/providers/hydrateProvider` — thin wrapper around TanStack's `HydrationBoundary`
- **Service layer**: e.g. `WorkspaceIssuesService` — defines `queryKey`, `queryFn`, `staleTime` for each query

## IMPORTANT: Do NOT pass values through props when a hook or `useParams` can provide them

The whole point of prefetch + dehydrate is that the **cache** is the source of truth on the client. Once you've prefetched a query on the server, every client component below `<HydrateProvider>` can read the same value via the matching `useSuspenseQuery` hook — for free, deduped, and reactive to invalidations.

**Rules:**

- If a child needs prefetched data, it must call the **counterpart hook** (`useX`) — not receive the data as a prop from the page.
- If a child needs a route param (`agentId`, `workspaceId`, `issueId`, etc.), it must call `useParams<{ ... }>()` from `next/navigation` — not receive it as a prop.
- The server `page.tsx` is responsible for `prefetchQuery(...)` only. It should pass **no data props and no route-param props** to the client tree it renders.
- This applies transitively: dialogs, cards, sub-sections — none of them should accept `agentId` / `workspaceId` / prefetched lists as props. Each reads from its own hook + `useParams`.

**Why this matters:**

- Passing prefetched data as a prop bypasses the cache. The child won't react to cache updates, optimistic mutations, or invalidations.
- Prop drilling forces a fresh array/object reference on every parent render → child memoization breaks → effects re-fire → duplicate fetches.
- Route params via props serialize through React's render tree; `useParams` reads them directly from the router with stable identity.
- When every consumer reads the same `queryKey`, TanStack Query dedupes — one network request, many readers.

**Bad** (page passes data + agentId down the tree):

```tsx
// ❌ page.tsx
const { agentId } = await params;
const result = await listIntegrations();
const integrations = isSuccessApiResult(result) ? result.data.data : [];

queryClient.prefetchQuery(environmentsListQuery(agentId));

return (
  <HydrateProvider state={dehydrate(queryClient)}>
    <EnvironmentsSection agentId={agentId} integrations={integrations} />
  </HydrateProvider>
);

// ❌ environments-section.tsx
export const EnvironmentsSection = ({ agentId, integrations }) => {
  const { data } = useEnvironments(agentId);
  return <AddEnvironmentDialog agentId={agentId} integrations={integrations} />;
};
```

**Good** (page only prefetches; children pull from hooks + `useParams`):

```tsx
// ✅ page.tsx
const { agentId } = await params;
const queryClient = getQueryClient();
queryClient.prefetchQuery(environmentsListQuery(agentId));
queryClient.prefetchQuery(integrationsListQuery()); // streamed, no await

return (
  <HydrateProvider state={dehydrate(queryClient)}>
    <Suspense fallback={<Skeleton />}>
      <EnvironmentsSection />
    </Suspense>
  </HydrateProvider>
);

// ✅ environments-section.tsx
'use client';
import { useParams } from 'next/navigation';

export const EnvironmentsSection = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const { data } = useEnvironments(agentId);
  return <AddEnvironmentDialog />;
};

// ✅ add-environment-dialog.tsx
'use client';
import { useParams } from 'next/navigation';

export const AddEnvironmentDialog = ({ open, onOpenChange }) => {
  const { agentId } = useParams<{ agentId: string }>();
  const { data: integrations } = useIntegrations();
  // ...
};
```

**Exceptions** — when props ARE the right answer:

- The value is local UI state owned by the parent (`open`, `onOpenChange`, `selected`, callbacks).
- The value is a list **item** that the parent has already iterated over (e.g. `<EnvironmentCard environment={env} />` inside a `.map()` — the card can't re-derive which item it is from a hook).
- The child needs a derived/filtered slice that only the parent has context to compute.

If a value can be obtained from a hook or `useParams`, prefer that over a prop.

## The Pattern

### Step 1: Server Page — Prefetch & Dehydrate

In a server component (`page.tsx`), prefetch all data the page needs:

```tsx
// app/dashboard/[workspaceId]/.../page.tsx  (SERVER COMPONENT)
import { dehydrate } from '@tanstack/react-query';
import getQueryClient from '@/lib/react-query/getQueryClient';
import { HydrateProvider } from '@/app/_common/providers/hydrateProvider';

const MyPage = async (props: PageProps<'...'>) => {
  const params = await props.params;
  const queryClient = getQueryClient();

  // CRITICAL vs NON-CRITICAL data distinction:

  // Option A: `await` — blocks rendering until resolved (critical data)
  await Promise.all([
    queryClient.prefetchQuery(MyService.getCriticalDataQuery({ id: params.id })),
    queryClient.prefetchQuery(MyService.getOtherCriticalQuery({ ... })),
  ]);

  // Option B: NO `await` — streams to client, Suspense shows fallback (non-critical data)
  queryClient.prefetchInfiniteQuery(
    MyService.getActivitiesInfiniteQuery({ id: params.id }),
  );

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrateProvider state={dehydratedState}>
      <MyPageContent />
    </HydrateProvider>
  );
};
```

**Key rules:**

- `await prefetchQuery(...)` — data is resolved before HTML is sent. Component renders with data immediately.
- `prefetchQuery(...)` (no await) — the **promise** is captured in the query cache. `dehydrate()` includes pending queries. The client receives a pending promise that resolves via streaming. The Suspense boundary shows a fallback until the data arrives.
- Use `Promise.all([...])` to parallelize multiple prefetches.
- Use `fetchQuery` instead of `prefetchQuery` when you need the return value on the server.

### Step 2: Shared Content Component — Suspense Boundaries

Create a component (can be server or client) that wraps child components in `<Suspense>`:

```tsx
// _components/my-page-content.tsx
import { Suspense } from 'react';

export const MyPageContent = () => {
  return (
    <>
      <Suspense fallback={<BodyPlaceholder />}>
        <MyPageBody />
      </Suspense>

      <Suspense fallback={<AsidePlaceholder />}>
        <MyPageAside />
      </Suspense>
    </>
  );
};
```

**Key rules:**

- Each `<Suspense>` boundary is independent — they stream in as their data resolves.
- Multiple `useSuspenseQuery` calls inside the **same** Suspense boundary will wait for **all** of them before rendering (they act as a combined container).
- Separate Suspense boundaries when sections can load independently.
- Always provide a meaningful fallback (skeleton/placeholder).

### Step 3: Client Components — useSuspenseQuery

Client components consume the hydrated (or streaming) data:

```tsx
// _components/my-page-body.tsx
'use client';

import { useSuspenseQuery } from '@tanstack/react-query';

export const MyPageBody = () => {
  const { data: item } = useSuspenseQuery(
    MyService.getCriticalDataQuery({ id }),
  );
  // No loading state needed — Suspense handles it
  // `data` is ALWAYS defined (never undefined)

  return <div>{item.name}</div>;
};
```

For infinite queries:

```tsx
'use client';

import { useSuspenseInfiniteQuery } from '@tanstack/react-query';

export const MyPageActivities = () => {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useSuspenseInfiniteQuery(MyService.getActivitiesInfiniteQuery({ id }));

  const allActivities = data.pages.flatMap((page) => page.activities);

  return (
    <>
      {allActivities.map((activity) => (
        <ActivityCard key={activity.id} activity={activity} />
      ))}
      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          Load more
        </button>
      )}
    </>
  );
};
```

### Step 4: Service Layer — Query Definitions

Define query configurations in a service class so both server and client use the same `queryKey` and `queryFn`:

```tsx
// _service/index.ts
import { myServerAction } from '@/server/my-domain/actions';

export class MyService {
  static getCriticalDataQuery(args: { id: string }) {
    return {
      queryKey: ['my-data', args.id],
      queryFn: () => myServerAction(args),
      staleTime: 300 * 1000, // 5 minutes
    };
  }

  static getActivitiesInfiniteQuery(args: { id: string }) {
    return {
      queryKey: ['my-activities', args.id],
      queryFn: ({ pageParam }: { pageParam: unknown }) =>
        getActivitiesAction({ ...args, cursor: pageParam as string }),
      initialPageParam: undefined as string | undefined,
      getNextPageParam: (lastPage: ActivitiesResponse) => lastPage.nextCursor,
      staleTime: 300 * 1000,
    };
  }
}
```

**Key rules:**

- Same query config object is used in both `prefetchQuery()` (server) and `useSuspenseQuery()` (client).
- `queryKey` must match exactly between server and client for hydration to work.
- `queryFn` calls server actions — these work on both server and client in Next.js.

## getQueryClient Setup

The singleton must include pending queries in dehydration for streaming to work:

```tsx
// lib/react-query/getQueryClient.tsx
import {
  QueryClient,
  defaultShouldDehydrateQuery,
  isServer,
} from '@tanstack/react-query';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
      },
      dehydrate: {
        // CRITICAL: include pending queries so un-awaited prefetches stream to client
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) ||
          query.state.status === 'pending',
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

export default function getQueryClient() {
  if (isServer) {
    // Server: always create a new client (one per request)
    return makeQueryClient();
  }
  // Client: reuse singleton (preserves cache across suspensions)
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}
```

**The `shouldDehydrateQuery` config is essential** — without it, pending (un-awaited) queries are excluded from dehydration and streaming breaks.

## HydrateProvider

Thin wrapper around TanStack's `HydrationBoundary`:

```tsx
// app/_common/providers/hydrateProvider.tsx
'use client';

import {
  HydrationBoundary,
  HydrationBoundaryProps,
} from '@tanstack/react-query';

export const HydrateProvider = (props: HydrationBoundaryProps) => {
  return <HydrationBoundary {...props} />;
};
```

## Streaming vs Blocking Decision Guide

| Scenario                               | Pattern                                    | Why                                              |
| -------------------------------------- | ------------------------------------------ | ------------------------------------------------ |
| Data needed for initial render / SEO   | `await prefetchQuery(...)`                 | Page waits, but content is in first HTML payload |
| Data for below-the-fold / secondary UI | `prefetchQuery(...)` (no await)            | HTML ships fast, data streams in via Suspense    |
| Data only needed on interaction        | Don't prefetch, use `useQuery()` on client | Fetches on demand, no server cost                |
| Infinite scroll / pagination           | `prefetchInfiniteQuery(...)` (no await)    | First page streams, user fetches more on scroll  |

## Common Mistakes

1. **Mismatched queryKeys** — Server prefetches with one key, client reads with another. Data won't hydrate.
2. **Missing `shouldDehydrateQuery`** — Pending queries won't be included in dehydration. Streaming silently breaks.
3. **Using `useQuery` instead of `useSuspenseQuery`** — `useQuery` won't throw a promise for Suspense to catch. Component renders with `undefined` data.
4. **Awaiting everything** — Defeats the purpose of streaming. Only await what's critical for first paint.
5. **No Suspense boundary** — `useSuspenseQuery` throws a promise. Without a `<Suspense>` ancestor, it crashes.
6. **Single Suspense boundary for everything** — All data must resolve before anything renders. Use separate boundaries for independent sections.
7. **Forgetting `'use client'`** — Components using `useSuspenseQuery` must be client components.
8. **Passing prefetched data or route params as props** — see the IMPORTANT section above. Children must read prefetched data via the counterpart `useX` hook and route params via `useParams`. Props drilling defeats the cache, churns identities, and causes duplicate/extra fetches.

## Reference

- [TanStack Query Suspense Streaming Example](https://tanstack.com/query/v5/docs/framework/react/examples/nextjs-suspense-streaming)
- [TanStack Query Advanced SSR Guide](https://tanstack.com/query/v5/docs/framework/react/guides/advanced-ssr)
- See `app/dashboard/[workspaceId]/agents/[agentId]/(issues-group)/issues/[issueId]/page.tsx` for a full working example in this codebase.
