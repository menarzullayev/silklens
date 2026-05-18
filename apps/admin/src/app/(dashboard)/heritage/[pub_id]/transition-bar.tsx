'use client';

import { useTransition } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { transitionHeritageAction } from '../actions';
import type { HeritageStatus, HeritageTransition } from '@/types/api';

const FLOWS: Readonly<
  Record<HeritageStatus, readonly { action: HeritageTransition; label: string }[]>
> = {
  draft: [{ action: 'submit', label: 'Submit for review' }],
  review: [
    { action: 'approve', label: 'Publish' },
    { action: 'reject', label: 'Reject' },
  ],
  published: [{ action: 'archive', label: 'Archive' }],
  archived: [{ action: 'restore', label: 'Restore' }],
  rejected: [{ action: 'restore', label: 'Restore to draft' }],
};

interface TransitionBarProps {
  readonly pubId: string;
  readonly status: HeritageStatus;
}

export function TransitionBar({ pubId, status }: TransitionBarProps): JSX.Element | null {
  const [pending, start] = useTransition();
  const actions = FLOWS[status];
  if (!actions || actions.length === 0) return null;
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
        <span className="text-muted-foreground">
          Current status: <strong className="text-foreground">{status}</strong>
        </span>
        <div className="flex gap-2">
          {actions.map((a) => (
            <Button
              key={a.action}
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => {
                start(async () => {
                  const result = await transitionHeritageAction(pubId, a.action);
                  if (result.ok) toast.success(`Status: ${a.action}`);
                  else toast.error(result.message ?? 'Transition failed');
                });
              }}
            >
              {a.label}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
