'use client';

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import type { ReactNode } from 'react';

export type DiffVersionId = number | 'draft';

interface VersionsContextValue {
  isDrawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  selectedVersion: number | null;
  selectVersion: (version: number | null) => void;
  isReadOnly: boolean;
  isPublishDialogOpen: boolean;
  openPublishDialog: () => void;
  closePublishDialog: () => void;
  showDiff: boolean;
  toggleDiff: () => void;
  diffFromVersion: DiffVersionId;
  diffToVersion: DiffVersionId;
  setDiffFromVersion: (version: DiffVersionId) => void;
  setDiffToVersion: (version: DiffVersionId) => void;
}

const VersionsContext = createContext<VersionsContextValue | null>(null);

export function useVersions() {
  const ctx = useContext(VersionsContext);

  if (!ctx) {
    throw new Error('useVersions must be used within VersionsProvider');
  }
  return ctx;
}

interface VersionsProviderProps {
  children: ReactNode;
}

export function VersionsProvider({ children }: VersionsProviderProps) {
  const [isDrawerOpen, setDrawerOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [isPublishDialogOpen, setPublishDialogOpen] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [diffFromVersion, setDiffFromVersion] = useState<DiffVersionId>('draft');
  const [diffToVersion, setDiffToVersion] = useState<DiffVersionId>('draft');

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const selectVersion = useCallback((version: number | null) => {
    setSelectedVersion(version);
    if (version === null) {
      setShowDiff(false);
    }
  }, []);

  const openPublishDialog = useCallback(() => setPublishDialogOpen(true), []);
  const closePublishDialog = useCallback(() => setPublishDialogOpen(false), []);

  const toggleDiff = useCallback(() => {
    setShowDiff((previous) => {
      const next = !previous;
      // When turning diff ON, seed From = selected version, To = draft
      if (next && selectedVersion !== null) {
        setDiffFromVersion(selectedVersion);
        setDiffToVersion('draft');
      }
      return next;
    });
  }, [selectedVersion]);

  const isReadOnly = selectedVersion !== null;

  const value = useMemo<VersionsContextValue>(
    () => ({
      isDrawerOpen,
      openDrawer,
      closeDrawer,
      selectedVersion,
      selectVersion,
      isReadOnly,
      isPublishDialogOpen,
      openPublishDialog,
      closePublishDialog,
      showDiff,
      toggleDiff,
      diffFromVersion,
      diffToVersion,
      setDiffFromVersion,
      setDiffToVersion,
    }),
    [
      isDrawerOpen,
      openDrawer,
      closeDrawer,
      selectedVersion,
      selectVersion,
      isReadOnly,
      isPublishDialogOpen,
      openPublishDialog,
      closePublishDialog,
      showDiff,
      toggleDiff,
      diffFromVersion,
      diffToVersion,
    ]
  );

  return <VersionsContext.Provider value={value}>{children}</VersionsContext.Provider>;
}
