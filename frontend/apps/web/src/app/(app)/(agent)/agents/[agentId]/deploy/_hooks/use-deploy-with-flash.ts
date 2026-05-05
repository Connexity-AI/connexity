'use client';

import { useState } from 'react';

import { useDeployEnvironment } from '@/app/(app)/(agent)/_hooks/use-deploy-environment';

const SUCCESS_FLASH_MS = 2000;

interface DeployArgs {
  environmentId: string;
  agentVersion: number;
}

/**
 * Wraps `useDeployEnvironment` with the transient "Deployed" success flash
 * the deploy button shows for ~2s after a successful deploy.
 *
 * Why this is its own hook:
 *   - The flash is needed at *two* call sites in `useEnvironmentCard` (the
 *     direct user-clicked deploy, and the auto-deploy that fires after a
 *     gated eval passes). Centralising it here means callers just call
 *     `mutate(args)` and never repeat the flash bookkeeping.
 *   - It removes the need for an effect watching `deploy.isSuccess`, which
 *     was the previous shape and re-fired whenever the mutation reference
 *     changed.
 *
 * Lifecycle notes:
 *   - The 2s timer is fire-and-forget. If the card unmounts mid-flash, the
 *     `setShowSuccess(false)` and `deploy.reset()` writes that fire after
 *     unmount are no-ops in React 18+, so we don't bother wiring cleanup.
 *   - We call `deploy.reset()` after the flash so the next click starts
 *     from a clean mutation state (no stale `isSuccess`, no stale data).
 */
export function useDeployWithFlash(agentId: string) {
  const deploy = useDeployEnvironment(agentId);
  const [showSuccess, setShowSuccess] = useState(false);

  const mutate = (args: DeployArgs) => {
    deploy.mutate(args, {
      onSuccess: () => {
        setShowSuccess(true);
        setTimeout(() => {
          setShowSuccess(false);
          deploy.reset();
        }, SUCCESS_FLASH_MS);
      },
    });
  };

  return {
    mutate,
    isPending: deploy.isPending,
    showSuccess,
    error: deploy.error,
  };
}
