'use client';

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import type { ReactNode } from 'react';

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

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const selectVersion = useCallback((version: number | null) => {
    setSelectedVersion(version);
  }, []);

  const openPublishDialog = useCallback(() => setPublishDialogOpen(true), []);
  const closePublishDialog = useCallback(() => setPublishDialogOpen(false), []);

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
    ]
  );

  return <VersionsContext.Provider value={value}>{children}</VersionsContext.Provider>;
}
