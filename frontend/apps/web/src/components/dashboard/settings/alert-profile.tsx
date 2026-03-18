'use client';

import { useEffect, useState } from 'react';

import { AlertCircle } from 'lucide-react';

import { Alert, AlertDescription } from '@workspace/ui/components/ui/alert';

import { waitMs } from '@/utils/wait';
import { DELAY } from '@/constants/delay';
import { EVENTS } from '@/constants/events';

import { AlertProfileUpdateEventArgs } from '@/types/events';
import type { FC } from 'react';

const { ALERT_PROFILE_UPDATE_SHOW } = EVENTS;
const { ALERT_AUTO_HIDE } = DELAY;

const AlertProfile: FC = () => {
  const [isShown, setIsShown] = useState(false);
  const [alertArgs, setAlertArgs] = useState<AlertProfileUpdateEventArgs | null>(null);

  useEffect(() => {
    // Note: must be sync function
    const handleShow = (event: CustomEvent<AlertProfileUpdateEventArgs>) => {
      setAlertArgs(event.detail);
      setIsShown(true);

      waitMs(ALERT_AUTO_HIDE).then(() => {
        setIsShown(false);
        setAlertArgs(null);
      });
    };

    window.addEventListener(ALERT_PROFILE_UPDATE_SHOW, handleShow as EventListener);

    return () => window.removeEventListener(ALERT_PROFILE_UPDATE_SHOW, handleShow as EventListener);
  }, []);

  if (!(isShown && alertArgs)) return null;

  const { variant, message } = alertArgs;

  return (
    <Alert variant={variant}>
      <AlertCircle className="h-4 w-4" />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
};

export default AlertProfile;
