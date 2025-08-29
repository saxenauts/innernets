import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium '
  + 'transition duration-150 ease-out will-change-transform '
  + 'focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 '
  + 'hover:shadow-md active:shadow-sm hover:-translate-y-px active:translate-y-0',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm',
        outline: 'border bg-background text-foreground hover:bg-muted/50',
        ghost: 'text-foreground hover:bg-muted/40',
        link: 'text-foreground underline-offset-4 hover:underline hover:text-primary',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-sm'
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 px-3',
        lg: 'h-10 px-6'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'default'
    }
  }
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
});
Button.displayName = 'Button';

export { Button, buttonVariants };
