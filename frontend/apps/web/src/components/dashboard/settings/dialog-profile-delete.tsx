'use client';

import { useActionState, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Loader2 } from 'lucide-react';

import { Alert, AlertDescription } from '@workspace/ui/components/ui/alert';
import { Button } from '@workspace/ui/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';

import { profileDeleteAction } from '@/actions/profile';
import { Message } from '@/client/types.gen';
import { isErrorApiResult, isSuccessApiResult } from '@/utils/api';
import { getApiErrorMessage } from '@/utils/error';
import { waitMs } from '@/utils/wait';
import { DELAY } from '@/constants/delay';
import { EVENTS } from '@/constants/events';
import { ROUTES } from '@/constants/routes';

import type { FC } from 'react';

const { DIALOG_PROFILE_DELETE_OPEN } = EVENTS;
const { DELETE_PROFILE_REDIRECT } = DELAY;
const { LOGIN } = ROUTES;

const DialogProfileDelete: FC = () => {
  const router = useRouter();

  const [isOpen, setIsOpen] = useState(false);
  const initialState = { data: undefined };
  const [state, formAction, isPending] = useActionState(profileDeleteAction, initialState);

  const isSuccess = isSuccessApiResult(state);
  const isError = isErrorApiResult(state);

  useEffect(() => {
    const handleOpen = () => setIsOpen(true);

    window.addEventListener(DIALOG_PROFILE_DELETE_OPEN, handleOpen as EventListener);

    return () =>
      window.removeEventListener(DIALOG_PROFILE_DELETE_OPEN, handleOpen as EventListener);
  }, []);

  const close = () => setIsOpen(false);

  useEffect(() => {
    if (!isSuccess) return;

    const closeDialogAndRedirect = async () => {
      await waitMs(DELETE_PROFILE_REDIRECT);
      close();

      router.push(LOGIN);
    };

    closeDialogAndRedirect();
  }, [isSuccess, router]);

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-red-600">Delete Account</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete your account? This action cannot be undone and will
            permanently remove all your data.
          </DialogDescription>
        </DialogHeader>

        {isSuccess && (
          <Alert variant="success">
            <AlertDescription>{`${(state.data as Message).message}. Redirecting...`}</AlertDescription>
          </Alert>
        )}

        {isError && (
          <Alert variant="destructive">
            <AlertDescription>{getApiErrorMessage(state.error)}</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <form action={formAction}>
            <Button
              variant="outline"
              onClick={close}
              type="button"
              disabled={isPending || isSuccess}
            >
              Cancel
            </Button>
            <Button variant="destructive" type="submit" disabled={isPending || isSuccess}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Deleting...
                </>
              ) : (
                'Delete Account'
              )}
            </Button>
          </form>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DialogProfileDelete;
