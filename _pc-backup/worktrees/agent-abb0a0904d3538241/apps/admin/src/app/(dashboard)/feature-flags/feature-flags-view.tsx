'use client';

import { useState, useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Pencil, Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { FeatureFlagOut, RolloutKind } from '@/types/api';
import { saveFlagAction } from './actions';

interface Props {
  readonly flags: readonly FeatureFlagOut[];
}

const ROLLOUT_KINDS: readonly { value: RolloutKind; label: string }[] = [
  { value: 'boolean', label: 'Boolean' },
  { value: 'percentage', label: 'Percentage' },
  { value: 'user_allowlist', label: 'User allowlist' },
  { value: 'user_denylist', label: 'User denylist' },
  { value: 'jsonl_rules', label: 'Rules (JSONL)' },
];

export function FeatureFlagsView({ flags }: Props): JSX.Element {
  const [editing, setEditing] = useState<FeatureFlagOut | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [pending, start] = useTransition();

  function toggle(flag: FeatureFlagOut, enabled: boolean): void {
    start(async () => {
      const result = await saveFlagAction({
        key: flag.key,
        enabled,
        rollout_kind: flag.rollout_kind,
        rollout_value: flag.rollout_value,
        description: flag.description,
      });
      if (result.ok) toast.success(`${flag.key} ${enabled ? 'enabled' : 'disabled'}`);
      else toast.error(result.message ?? 'Save failed');
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" /> New flag
        </Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Key</TableHead>
              <TableHead>Enabled</TableHead>
              <TableHead>Rollout</TableHead>
              <TableHead>Description</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {flags.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  No flags configured.
                </TableCell>
              </TableRow>
            ) : (
              flags.map((f) => (
                <TableRow key={f.key}>
                  <TableCell className="font-mono text-xs">{f.key}</TableCell>
                  <TableCell>
                    <Switch
                      checked={f.enabled}
                      disabled={pending}
                      onCheckedChange={(v) => toggle(f, v)}
                      aria-label={`Toggle ${f.key}`}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="capitalize">
                      {f.rollout_kind.replace(/_/g, ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-md truncate text-xs text-muted-foreground">
                    {f.description ?? '—'}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => setEditing(f)}
                      aria-label={`Edit ${f.key}`}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <FlagDialog
        open={editing !== null}
        flag={editing}
        onClose={() => setEditing(null)}
      />
      <FlagDialog
        open={createOpen}
        flag={null}
        onClose={() => setCreateOpen(false)}
      />
    </div>
  );
}

const dialogSchema = z.object({
  key: z.string().min(2).max(128),
  enabled: z.boolean(),
  rollout_kind: z.enum([
    'boolean',
    'percentage',
    'user_allowlist',
    'user_denylist',
    'jsonl_rules',
  ]),
  rollout_value_json: z.string(),
  description: z.string().max(512).optional(),
});
type DialogValues = z.infer<typeof dialogSchema>;

interface FlagDialogProps {
  readonly open: boolean;
  readonly flag: FeatureFlagOut | null;
  readonly onClose: () => void;
}

function FlagDialog({ open, flag, onClose }: FlagDialogProps): JSX.Element {
  const [pending, start] = useTransition();
  const form = useForm<DialogValues>({
    resolver: zodResolver(dialogSchema),
    defaultValues: flag
      ? {
          key: flag.key,
          enabled: flag.enabled,
          rollout_kind: flag.rollout_kind,
          rollout_value_json: JSON.stringify(flag.rollout_value, null, 2),
          description: flag.description ?? '',
        }
      : {
          key: '',
          enabled: false,
          rollout_kind: 'boolean',
          rollout_value_json: '{}',
          description: '',
        },
    values: flag
      ? {
          key: flag.key,
          enabled: flag.enabled,
          rollout_kind: flag.rollout_kind,
          rollout_value_json: JSON.stringify(flag.rollout_value, null, 2),
          description: flag.description ?? '',
        }
      : undefined,
  });

  function onSubmit(values: DialogValues): void {
    let parsedJson: Record<string, unknown>;
    try {
      parsedJson = JSON.parse(values.rollout_value_json || '{}');
      if (parsedJson === null || typeof parsedJson !== 'object' || Array.isArray(parsedJson)) {
        throw new Error('rollout_value must be a JSON object');
      }
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : 'Invalid JSON');
      return;
    }
    start(async () => {
      const result = await saveFlagAction({
        key: values.key,
        enabled: values.enabled,
        rollout_kind: values.rollout_kind,
        rollout_value: parsedJson,
        description: values.description || null,
      });
      if (result.ok) {
        toast.success(`${values.key} saved`);
        onClose();
        form.reset();
      } else {
        toast.error(result.message ?? 'Save failed');
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={(v) => (v ? null : onClose())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{flag ? 'Edit feature flag' : 'Create feature flag'}</DialogTitle>
          <DialogDescription>
            Rollout JSON shape depends on `rollout_kind` —
            <code className="ml-1">{`{"percentage": 25}`}</code> for percentage,
            <code className="ml-1">{`{"users": ["uuid", …]}`}</code> for allowlist.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-1">
            <Label htmlFor="flag-key">Key</Label>
            <Input id="flag-key" {...form.register('key')} disabled={flag !== null} />
          </div>
          <div className="flex items-center justify-between rounded-md border p-3">
            <span className="text-sm">Enabled</span>
            <Switch
              checked={form.watch('enabled')}
              onCheckedChange={(v) => form.setValue('enabled', v, { shouldDirty: true })}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="rollout_kind">Rollout kind</Label>
            <Select
              value={form.watch('rollout_kind')}
              onValueChange={(v) =>
                form.setValue('rollout_kind', v as RolloutKind, { shouldDirty: true })
              }
            >
              <SelectTrigger id="rollout_kind">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLLOUT_KINDS.map((k) => (
                  <SelectItem key={k.value} value={k.value}>
                    {k.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="rollout_value_json">Rollout value (JSON)</Label>
            <Textarea
              id="rollout_value_json"
              rows={6}
              className="font-mono text-xs"
              {...form.register('rollout_value_json')}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" rows={2} {...form.register('description')} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={pending}>
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
