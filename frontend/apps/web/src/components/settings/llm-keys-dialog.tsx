'use client';

import { useEffect, useState } from 'react';

import { useQuery } from '@tanstack/react-query';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@workspace/ui/components/ui/dialog';
import { Skeleton } from '@workspace/ui/components/ui/skeleton';

import { getLlmCredentials } from '@/actions/company';
import { isSuccessApiResult } from '@/utils/api';

import FormLlmKeySettings from './form-llm-key-settings';

import type { CompanyLlmCredentialsPublic } from '@/client/types.gen';
import type { FC } from 'react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const LlmKeysDialog: FC<Props> = ({ open, onOpenChange }) => {
  // Refetch the masked credentials each time the dialog opens so the form
  // shows the current state even after a previous save in the same session.
  const [version, setVersion] = useState(0);
  useEffect(() => {
    if (open) setVersion((v) => v + 1);
  }, [open]);

  const query = useQuery({
    queryKey: ['company', 'llm-credentials', version],
    queryFn: async (): Promise<CompanyLlmCredentialsPublic | null> => {
      const result = await getLlmCredentials();
      return isSuccessApiResult(result) ? result.data : null;
    },
    enabled: open,
    staleTime: 0,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>LLM API keys</DialogTitle>
          <DialogDescription>
            Used for test case generation and eval judging. Stored encrypted at rest.
          </DialogDescription>
        </DialogHeader>

        {query.isLoading ? (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-20" />
          </div>
        ) : (
          <FormLlmKeySettings
            current={query.data ?? null}
            onSaved={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
};

export default LlmKeysDialog;
