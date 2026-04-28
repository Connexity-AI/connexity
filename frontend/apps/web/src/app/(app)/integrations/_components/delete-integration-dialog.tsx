'use client';

import { useState } from 'react';

import { useQueryClient } from '@tanstack/react-query';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@workspace/ui/components/ui/alert-dialog';

import { deleteIntegration } from '@/actions/integrations';
import { integrationKeys } from '@/constants/query-keys';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';

import type { IntegrationPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  integration: IntegrationPublic;
}

export const DeleteIntegrationDialog: FC<Props> = ({
  open,
  onOpenChange,
  integration,
}) => {
  const queryClient = useQueryClient();
  const [isPending, setIsPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleConfirm = async () => {
    setIsPending(true);
    setErrorMessage(null);
    const result = await deleteIntegration(integration.id);
    setIsPending(false);
    if (isSuccessApiResult(result)) {
      void queryClient.invalidateQueries({ queryKey: integrationKeys.all });
      onOpenChange(false);
    } else if (isErrorApiResult(result)) {
      setErrorMessage(getApiErrorMessage(result.error));
    }
  };

  return (
    <AlertDialog
      open={open}
      onOpenChange={(o) => {
        if (!isPending) {
          setErrorMessage(null);
          onOpenChange(o);
        }
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete integration</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete &ldquo;{integration.name}&rdquo;? This action cannot
            be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {errorMessage && (
          <p className="text-sm text-destructive px-1">{errorMessage}</p>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              void handleConfirm();
            }}
            disabled={isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isPending ? 'Deleting…' : 'Delete'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
