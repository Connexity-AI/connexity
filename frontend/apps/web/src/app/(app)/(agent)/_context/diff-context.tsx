'use client';

/**
 * DiffContext — owns the "view diff" UI state on the agent edit page.
 *
 * When the user is viewing a historical version (read-only mode, driven by
 * `VersionsContext.selectedVersion`), they can click "View diff" in the
 * read-only banner to compare two versions side-by-side. This context
 * holds that UI state:
 *
 *   - `showDiff`         — is the diff view currently visible?
 *   - `diffFromVersion`  — left side of the comparison
 *   - `diffToVersion`    — right side of the comparison
 *
 * The actual diffing/rendering lives in `<DiffControls>` + `<DiffView>`
 * inside the prompt tab. This context just holds state and exposes
 * setters.
 *
 * Why is this separate from VersionsContext?
 *   VersionsContext tracks "which version is the user looking at" (drawer
 *   open, selected version, publish dialog). Diff state is only meaningful
 *   while a version is selected, and it has its own reset/seed rules, so
 *   splitting it keeps each context small and single-purpose. See
 *   `versions-context.tsx` for the rest of the versions UI state.
 *
 * Lifecycle:
 *   Both providers are mounted once per agent edit page. When the user
 *   navigates away the providers unmount and all state resets — there's
 *   no persistence across sessions.
 */
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import { useVersions } from '@/app/(app)/(agent)/_context/versions-context';

import type { ReactNode } from 'react';

/**
 * Identifier for one side of the diff. Either a concrete historical
 * version number, or the sentinel `'draft'` meaning "the current,
 * unsaved draft the user is editing." Using a sentinel (instead of,
 * say, `null`) keeps the type closed — every diff side is exactly one
 * of these two shapes, and consumers can exhaustively switch on it.
 */
export type DiffVersionId = number | 'draft';

interface DiffContextValue {
  showDiff: boolean;
  toggleDiff: () => void;
  diffFromVersion: DiffVersionId;
  diffToVersion: DiffVersionId;
  setDiffFromVersion: (version: DiffVersionId) => void;
  setDiffToVersion: (version: DiffVersionId) => void;
}

const DiffContext = createContext<DiffContextValue | null>(null);

export function useDiff() {
  const ctx = useContext(DiffContext);

  if (!ctx) {
    throw new Error('useDiff must be used within DiffProvider');
  }
  return ctx;
}

interface DiffProviderProps {
  children: ReactNode;
}

export function DiffProvider({ children }: DiffProviderProps) {
  // DiffProvider must be rendered *inside* VersionsProvider so this read
  // works. See agents/[agentId]/page.tsx for the nesting order.
  const { selectedVersion } = useVersions();

  const [showDiff, setShowDiff] = useState(false);
  // Both sides default to the draft. They get meaningfully seeded the
  // first time the user opens diff view via `toggleDiff` below.
  const [diffFromVersion, setDiffFromVersion] = useState<DiffVersionId>('draft');
  const [diffToVersion, setDiffToVersion] = useState<DiffVersionId>('draft');

  // --- Reset diff view when the user exits read-only mode ---------------
  //
  // When `selectedVersion` goes back to `null` (user clicked "Back to
  // draft"), we want `showDiff` to reset to `false` so that re-entering
  // read-only mode later starts fresh without the diff already open.
  //
  // We use the "adjust state during render" pattern from the React docs:
  // https://react.dev/reference/react/useState#storing-information-from-previous-renders
  //
  // Why not `useEffect`?
  //   An effect runs *after* commit, so children would render once with
  //   the stale combination `showDiff=true` + `selectedVersion=null`,
  //   then re-render a second time after the effect fires. ESLint flags
  //   this as "cascading renders" for exactly that reason.
  //
  // How the pattern works:
  //   We store the previous `selectedVersion` in its own state. On each
  //   render we compare it to the current value; if they differ, we call
  //   `setState` synchronously during render. React notices the pending
  //   state updates, discards the in-progress render, and restarts with
  //   the new state *before* committing anything to the DOM. Consumers
  //   never see the stale state.
  const [prevSelectedVersion, setPrevSelectedVersion] = useState(selectedVersion);

  if (prevSelectedVersion !== selectedVersion) {
    setPrevSelectedVersion(selectedVersion);

    if (selectedVersion === null) {
      setShowDiff(false);
    }
  }

  // --- Toggle diff view -------------------------------------------------
  //
  // When turning the diff ON for the first time, pre-fill the comparison
  // sides with a sensible default: "the version the user is currently
  // looking at" vs. "the live draft." This matches the mental model of
  // "show me what changed since this old version." The user can then
  // swap either side via the <DiffControls> dropdowns.
  //
  // Turning diff OFF is just a flag flip — we leave the from/to values
  // alone so that toggling back on restores the previous comparison.
  const toggleDiff = useCallback(() => {
    setShowDiff((previous) => {
      const next = !previous;

      if (next && selectedVersion !== null) {
        setDiffFromVersion(selectedVersion);
        setDiffToVersion('draft');
      }
      return next;
    });
  }, [selectedVersion]);

  const value = useMemo<DiffContextValue>(
    () => ({
      showDiff,
      toggleDiff,
      diffFromVersion,
      diffToVersion,
      setDiffFromVersion,
      setDiffToVersion,
    }),
    [showDiff, toggleDiff, diffFromVersion, diffToVersion]
  );

  return <DiffContext.Provider value={value}>{children}</DiffContext.Provider>;
}
