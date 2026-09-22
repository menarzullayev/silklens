'use client';

import { useState, useTransition } from 'react';
import { toast } from 'sonner';

import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { AiModelOut } from '@/types/api';
import { patchAiModelAction } from './actions';

interface Props {
  readonly models: readonly AiModelOut[];
}

function pickName(name: Record<string, string>): string {
  return name.en ?? name.uz ?? Object.values(name)[0] ?? '';
}

export function ModelsTable({ models }: Props): JSX.Element {
  const [rows, setRows] = useState(models);
  const [pending, start] = useTransition();

  function persist(slug: string, patch: { is_enabled?: boolean; sort_order?: number }): void {
    start(async () => {
      const result = await patchAiModelAction({ slug, ...patch });
      if (result.ok) toast.success(`${slug} updated`);
      else toast.error(result.message ?? 'Save failed');
    });
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Slug</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Task</TableHead>
            <TableHead>Provider</TableHead>
            <TableHead>Enabled</TableHead>
            <TableHead>Sort order</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                No models registered yet.
              </TableCell>
            </TableRow>
          ) : (
            rows.map((m) => (
              <TableRow key={m.slug}>
                <TableCell className="font-mono text-xs">{m.slug}</TableCell>
                <TableCell>{pickName(m.name)}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="capitalize">
                    {m.task_type}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{m.provider_slug}</TableCell>
                <TableCell>
                  <Switch
                    checked={m.is_enabled}
                    disabled={pending}
                    aria-label={`Toggle ${m.slug}`}
                    onCheckedChange={(v) => {
                      setRows((prev) =>
                        prev.map((row) =>
                          row.slug === m.slug ? { ...row, is_enabled: v } : row,
                        ),
                      );
                      persist(m.slug, { is_enabled: v });
                    }}
                  />
                </TableCell>
                <TableCell>
                  <Input
                    type="number"
                    value={m.sort_order}
                    className="w-20 font-mono"
                    onChange={(e) => {
                      const value = parseInt(e.target.value, 10);
                      if (Number.isFinite(value)) {
                        setRows((prev) =>
                          prev.map((row) =>
                            row.slug === m.slug ? { ...row, sort_order: value } : row,
                          ),
                        );
                      }
                    }}
                    onBlur={(e) => {
                      const value = parseInt(e.target.value, 10);
                      if (Number.isFinite(value) && value !== m.sort_order) {
                        persist(m.slug, { sort_order: value });
                      }
                    }}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
