'use client';

import { useEffect, useState, useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Plus, Pencil } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { LocaleTextInput } from '@/components/forms/locale-text-input';
import type { TenantOut, TenantStatus } from '@/types/api';
import { createTenantAction, patchTenantAction } from './actions';

const createSchema = z.object({
  slug: z
    .string()
    .min(2)
    .max(64)
    .regex(/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/, 'lowercase, digits, dashes'),
});

type CreateValues = z.infer<typeof createSchema>;

const STATUSES: readonly { value: TenantStatus; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'archived', label: 'Archived' },
];

function pickName(name: Record<string, string>): string {
  return name.en ?? name.uz ?? Object.values(name)[0] ?? '';
}

interface TenantsViewProps {
  readonly items: readonly TenantOut[];
}

export function TenantsView({ items }: TenantsViewProps): JSX.Element {
  const [createOpen, setCreateOpen] = useState(false);
  const [editTenant, setEditTenant] = useState<TenantOut | null>(null);
  const [createName, setCreateName] = useState<Record<string, string>>({ en: '' });
  const [pending, start] = useTransition();
  const createForm = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { slug: '' },
  });

  function onCreate(values: CreateValues): void {
    const filtered = Object.fromEntries(
      Object.entries(createName).filter(([, v]) => v.trim()),
    );
    if (Object.keys(filtered).length === 0) {
      toast.error('Provide at least one display name translation.');
      return;
    }
    start(async () => {
      const result = await createTenantAction({
        slug: values.slug,
        display_name: filtered,
      });
      if (result.ok) {
        toast.success('Tenant created');
        setCreateOpen(false);
        createForm.reset();
        setCreateName({ en: '' });
      } else {
        toast.error(result.message ?? 'Create failed');
      }
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4" /> New tenant
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create tenant</DialogTitle>
              <DialogDescription>
                Provisions a new row in `tenants` with active status, free
                plan. Branding can be configured immediately after.
              </DialogDescription>
            </DialogHeader>
            <form
              className="space-y-4"
              onSubmit={createForm.handleSubmit(onCreate)}
            >
              <div className="space-y-2">
                <Label htmlFor="slug">Slug</Label>
                <Input id="slug" placeholder="acme" {...createForm.register('slug')} />
                {createForm.formState.errors.slug ? (
                  <p className="text-xs text-destructive">
                    {createForm.formState.errors.slug.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label>Display name (per language)</Label>
                <LocaleTextInput
                  value={createName}
                  onChange={setCreateName}
                  placeholder="Acme Heritage Foundation"
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={pending}>
                  Create
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Slug</TableHead>
              <TableHead>Display name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  No tenants yet.
                </TableCell>
              </TableRow>
            ) : (
              items.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="font-mono text-xs">{t.slug}</TableCell>
                  <TableCell>{pickName(t.display_name)}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="capitalize">
                      {t.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="capitalize">{t.plan_tier}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(t.updated_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => setEditTenant(t)}
                      aria-label={`Edit ${t.slug}`}
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

      <EditTenantDialog
        tenant={editTenant}
        onClose={() => setEditTenant(null)}
      />
    </div>
  );
}

const editSchema = z.object({
  status: z.enum(['active', 'suspended', 'archived']),
  plan_tier: z.string().min(1).max(32),
});

type EditValues = z.infer<typeof editSchema>;

interface EditTenantDialogProps {
  readonly tenant: TenantOut | null;
  readonly onClose: () => void;
}

function EditTenantDialog({ tenant, onClose }: EditTenantDialogProps): JSX.Element {
  const [name, setName] = useState<Record<string, string>>({});
  const [pending, start] = useTransition();
  const form = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      status: tenant?.status ?? 'active',
      plan_tier: tenant?.plan_tier ?? 'free',
    },
    values: tenant
      ? { status: tenant.status, plan_tier: tenant.plan_tier }
      : undefined,
  });

  useEffect(() => {
    if (tenant) setName(tenant.display_name);
    else setName({});
  }, [tenant]);

  function onSubmit(values: EditValues): void {
    if (!tenant) return;
    const filtered = Object.fromEntries(
      Object.entries(name).filter(([, v]) => v.trim()),
    );
    start(async () => {
      const result = await patchTenantAction(tenant.slug, {
        ...values,
        display_name: Object.keys(filtered).length > 0 ? filtered : undefined,
      });
      if (result.ok) {
        toast.success('Tenant updated');
        onClose();
        setName({});
      } else {
        toast.error(result.message ?? 'Update failed');
      }
    });
  }

  return (
    <Dialog
      open={tenant !== null}
      onOpenChange={(open) => {
        if (!open) {
          onClose();
          setName({});
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit tenant</DialogTitle>
          <DialogDescription>
            Slug is immutable. Update display name, status, plan tier.
          </DialogDescription>
        </DialogHeader>
        {tenant ? (
          <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
            <div className="space-y-1">
              <Label>Slug</Label>
              <Input value={tenant.slug} disabled />
            </div>
            <div className="space-y-2">
              <Label>Display name</Label>
              <LocaleTextInput value={name} onChange={setName} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="status">Status</Label>
                <Select
                  value={form.watch('status')}
                  onValueChange={(v) =>
                    form.setValue('status', v as TenantStatus, { shouldDirty: true })
                  }
                >
                  <SelectTrigger id="status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUSES.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="plan_tier">Plan tier</Label>
                <Input id="plan_tier" {...form.register('plan_tier')} />
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={pending}>
                Save
              </Button>
            </DialogFooter>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
