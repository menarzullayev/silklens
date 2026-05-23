'use client';

import { useTransition } from 'react';
import { toast } from 'sonner';
import { CheckCircle, XCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { HeritageOut, HeritageStatus } from '@/types/api';
import { approveHeritageAction, rejectHeritageAction } from './actions';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pickName(name: Record<string, string>): string {
  return name.en ?? name.uz ?? name.ru ?? Object.values(name)[0] ?? '—';
}

function statusVariant(
  status: HeritageStatus,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'published':
      return 'default';
    case 'review':
      return 'secondary';
    case 'rejected':
      return 'destructive';
    default:
      return 'outline';
  }
}

function statusLabel(status: HeritageStatus): string {
  switch (status) {
    case 'review':
      return 'In Review';
    case 'published':
      return 'Published';
    case 'draft':
      return 'Draft';
    case 'rejected':
      return 'Rejected';
    case 'archived':
      return 'Archived';
    default:
      return status;
  }
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return String(iso);
  }
}

// ---------------------------------------------------------------------------
// Row component — isolated transition so one row's pending doesn't freeze all
// ---------------------------------------------------------------------------

interface ModerationRowProps {
  readonly item: HeritageOut;
}

function ModerationRow({ item }: ModerationRowProps): JSX.Element {
  const [pending, start] = useTransition();

  function approve(): void {
    start(async () => {
      const result = await approveHeritageAction(item.pub_id);
      if (result.ok) toast.success(`"${pickName(item.name)}" published`);
      else toast.error(result.message ?? 'Approve failed');
    });
  }

  function reject(): void {
    start(async () => {
      const result = await rejectHeritageAction(item.pub_id);
      if (result.ok) toast.success(`"${pickName(item.name)}" rejected`);
      else toast.error(result.message ?? 'Reject failed');
    });
  }

  return (
    <TableRow key={item.pub_id} aria-busy={pending}>
      <TableCell className="font-medium">{pickName(item.name)}</TableCell>
      <TableCell className="capitalize text-muted-foreground">
        {item.kind_slug.replace(/_/g, ' ')}
      </TableCell>
      <TableCell className="text-muted-foreground">
        {item.country_code ?? '—'}
      </TableCell>
      <TableCell>
        <Badge variant={statusVariant(item.status)}>
          {statusLabel(item.status)}
        </Badge>
      </TableCell>
      <TableCell className="text-muted-foreground">
        {formatDate(undefined)}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={pending || item.status !== 'review'}
            onClick={approve}
            className="gap-1 text-green-700 hover:bg-green-50 hover:text-green-700 dark:text-green-400 dark:hover:bg-green-950"
          >
            <CheckCircle className="h-3.5 w-3.5" />
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={pending || item.status !== 'review'}
            onClick={reject}
            className="gap-1 text-destructive hover:bg-destructive/5 hover:text-destructive"
          >
            <XCircle className="h-3.5 w-3.5" />
            Reject
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

interface ModerationTableProps {
  readonly items: readonly HeritageOut[];
  readonly total: number;
}

export function ModerationTable({
  items,
  total,
}: ModerationTableProps): JSX.Element {
  if (items.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        No heritage entries are currently awaiting moderation.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        {total} entr{total === 1 ? 'y' : 'ies'} awaiting review
      </p>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead>Country</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead className="w-40">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <ModerationRow key={item.pub_id} item={item} />
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
