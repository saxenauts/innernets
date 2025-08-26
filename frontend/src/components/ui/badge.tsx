import * as React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'outline' | 'new';
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const base = 'inline-flex items-center rounded-full border px-2 py-0.5 text-xs';
  const styles =
    variant === 'outline'
      ? 'border text-muted-foreground'
      : variant === 'new'
      ? 'bg-primary/10 border-primary/20 text-primary'
      : 'bg-muted text-muted-foreground border';
  return <span className={cn(base, styles, className)} {...props} />;
}
