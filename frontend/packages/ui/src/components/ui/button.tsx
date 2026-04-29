import * as React from 'react';

import { Slot, Slottable } from '@radix-ui/react-slot';
import { cva } from 'class-variance-authority';

import { cn } from '@workspace/ui/lib/utils';

import type { VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 cursor-pointer',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
        success: 'bg-green-600 text-white hover:bg-green-700 shadow',
      },
      size: {
        sm: 'text-sm h-9 px-3 py-2 rounded-md',
        md: 'text-sm h-10 px-4 py-2.5',
        lg: 'text-base h-11 px-4 py-2.5 rounded-md',
        xl: 'text-lg h-12 px-4 py-3 rounded-md',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
);

export const iconVariants = cva('', {
  variants: {
    variant: {
      primary: 'text-primary-foreground',
      destructive: '',
      outline: '',
      secondary: '',
      ghost: 'text-muted-foreground',
      link: '',
      success: 'text-white',
    },
    size: {
      sm: 'px-2.5 py-2.5',
      md: 'px-2.5 py-2.5',
      lg: 'px-3 py-3',
      xl: 'px-3.5 py-3.5',
      icon: '',
    },
  },
  defaultVariants: {
    variant: 'primary',
    size: 'sm',
  },
});

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  startIcon?: React.ElementType;
  endIcon?: React.ElementType;
  icon?: React.ElementType;
  ref?: React.Ref<HTMLButtonElement>;
}

const Button: React.FC<ButtonProps> = ({
  className,
  variant,
  size,
  startIcon: StartIcon,
  icon: Icon,
  endIcon: EndIcon,
  asChild = false,
  ref,
  children,
  ...props
}) => {
  const Comp = asChild ? Slot : 'button';

  return (
    <Comp
      className={cn(
        buttonVariants({ variant, size, className }),
        Icon && iconVariants({ variant, size }),
      )}
      ref={ref}
      {...props}
    >
      {StartIcon && (
        <StartIcon
          size={size === 'sm' ? 16 : 20}
          className={cn(iconVariants({ variant }), 'p-0 mr-2')}
        />
      )}
      {Icon && (
        <Icon size={size === 'sm' ? 16 : 20} className="text-current" />
      )}
      {!Icon && <Slottable>{children}</Slottable>}
      {EndIcon && (
        <EndIcon
          size={size === 'sm' ? 16 : 20}
          className={cn(iconVariants({ variant }), 'p-0 ml-2')}
        />
      )}
    </Comp>
  );
};
Button.displayName = 'Button';

export { Button, buttonVariants };
