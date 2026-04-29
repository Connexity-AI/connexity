'use client';

import { createContext, useContext } from 'react';

import type { ReactNode } from 'react';

const ReadOnlyContext = createContext(false);

export function CreateEvalReadOnlyProvider({
  readOnly,
  children,
}: {
  readOnly: boolean;
  children: ReactNode;
}) {
  return <ReadOnlyContext.Provider value={readOnly}>{children}</ReadOnlyContext.Provider>;
}

export function useCreateEvalReadOnly() {
  return useContext(ReadOnlyContext);
}
