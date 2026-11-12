'use client';

import * as React from 'react';

import * as DialogPrimitive from '@radix-ui/react-dialog';

import { cn } from '@workspace/ui/lib/utils';

/** A small dialog on surface-2 over a dimmed page (Connexity Sidebar, New workspace). */
const Dialog = DialogPrimitive.Root;
const DialogClose = DialogPrimitive.Close;

const DialogContent: React.FC<React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>> = ({
  className,
  children,
  ...props
}) => (
  <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-backdrop" />
    <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center p-6">
      <DialogPrimitive.Content
        className={cn(
          'pointer-events-auto flex w-full max-w-[400px] flex-col gap-5 rounded-xl border border-hairline bg-surface-2 p-6 text-body text-ink shadow-dialog outline-none',
          className
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </div>
  </DialogPrimitive.Portal>
);

const DialogTitle: React.FC<React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>> = ({
  className,
  ...props
}) => (
  <DialogPrimitive.Title
    className={cn('m-0 text-heading font-medium text-ink', className)}
    {...props}
  />
);

const DialogDescription = DialogPrimitive.Description;

export { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle };
