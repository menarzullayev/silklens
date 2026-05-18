import { type ReactNode } from 'react';
import { type LucideIcon, Inbox } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  readonly title: string;
  readonly description?: string;
  readonly icon?: LucideIcon;
  readonly action?: ReactNode;
  readonly className?: string;
}

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className,
}: EmptyStateProps): JSX.Element {
  return (
    <Card className={cn('border-dashed', className)}>
      <CardContent className="flex flex-col items-center justify-center gap-2 py-12 text-center">
        <Icon
          aria-hidden
          className="h-10 w-10 text-muted-foreground"
        />
        <h3 className="text-base font-semibold">{title}</h3>
        {description ? (
          <p className="max-w-md text-sm text-muted-foreground">{description}</p>
        ) : null}
        {action ? <div className="mt-2">{action}</div> : null}
      </CardContent>
    </Card>
  );
}

interface ErrorStateProps {
  readonly title: string;
  readonly message: string;
  readonly className?: string;
}

export function ErrorState({
  title,
  message,
  className,
}: ErrorStateProps): JSX.Element {
  return (
    <Card
      role="alert"
      className={cn('border-destructive/40 bg-destructive/5', className)}
    >
      <CardContent className="py-8 text-center">
        <h3 className="text-base font-semibold text-destructive">{title}</h3>
        <p className="mt-1 text-sm text-destructive/80">{message}</p>
      </CardContent>
    </Card>
  );
}
