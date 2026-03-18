import { PHASE_PRODUCTION_BUILD } from 'next/constants';

export const isServer = (): boolean => typeof window === 'undefined';

export const isClient = (): boolean => !isServer();

// eslint-disable-next-line turbo/no-undeclared-env-vars
export const isNextBuild = (): boolean => process.env.NEXT_PHASE === PHASE_PRODUCTION_BUILD;
