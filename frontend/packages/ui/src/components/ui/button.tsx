import * as React from 'react';

import { Slot } from '@radix-ui/react-slot';
import { cva } from 'class-variance-authority';

import { cn } from '@workspace/ui/lib/utils';

import type { VariantProps } from 'class-variance-authority';

/**
 * Connexity Design System button: primary (filled with accent, the one main action),
 * secondary (outlined) and ghost (quiet, small).
 */
const buttonVariants = cva(
  'inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-md outline-none focus-visible:ring-2 focus-visible:ring-border-control disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'h-9 bg-accent-ink px-4 text-body font-medium text-on-accent hover:opacity-90',
        secondary: 'h-9 border border-border-control px-3 text-body text-ink hover:bg-wash',
        ghost:
          'h-7 px-2 text-label text-ink-secondary hover:bg-wash hover:text-ink [&_svg]:size-3.5',
      },
    },
    defaultVariants: {
      variant: 'primary',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  ref?: React.Ref<HTMLButtonElement>;
}

const Button: React.FC<ButtonProps> = ({ className, variant, asChild = false, ref, ...props }) => {
  const Comp = asChild ? Slot : 'button';

  return <Comp className={cn(buttonVariants({ variant, className }))} ref={ref} {...props} />;
};
Button.displayName = 'Button';

export { Button, buttonVariants };
