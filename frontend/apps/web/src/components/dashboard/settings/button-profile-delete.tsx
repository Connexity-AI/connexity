import { AlertTriangle } from 'lucide-react';

import { Button } from '@workspace/ui/components/ui/button';

import { EVENTS } from '@/constants/events';

import type { FC } from 'react';

const { DIALOG_PROFILE_DELETE_OPEN } = EVENTS;

const ButtonProfileDelete: FC = () => {
  const openDialogProfileDelete = () => {
    const openEvent = new CustomEvent(DIALOG_PROFILE_DELETE_OPEN);
    window.dispatchEvent(openEvent);
  };

  return (
    <div className="rounded-lg border border-red-200 dark:border-red-800 p-4">
      <h3 className="text-lg font-medium text-red-600 dark:text-red-400 mb-2">Delete Account</h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Once you delete your account, there is no going back. Please be certain.
      </p>
      <Button variant="destructive" onClick={openDialogProfileDelete}>
        <AlertTriangle className="mr-2 h-4 w-4" />
        Delete Account
      </Button>
    </div>
  );
};

export default ButtonProfileDelete;
