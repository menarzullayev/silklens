'use client';

import { useState, useTransition } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { LocaleTextInput } from '@/components/forms/locale-text-input';
import { createHeritageAction, patchHeritageAction } from './actions';
import type { HeritageOut, HeritageStatus } from '@/types/api';

interface Option {
  readonly value: string;
  readonly label: string;
}

interface HeritageFormProps {
  readonly mode: 'create' | 'edit';
  readonly initial?: HeritageOut;
  readonly kindOptions: readonly Option[];
  readonly countryOptions: readonly Option[];
}

const schema = z.object({
  kind_slug: z.string().min(2),
  country_code: z.string().optional(),
  latitude: z
    .preprocess(toNum, z.number().min(-90).max(90).optional().nullable())
    .optional(),
  longitude: z
    .preprocess(toNum, z.number().min(-180).max(180).optional().nullable())
    .optional(),
  period_start_year: z
    .preprocess(toNum, z.number().int().optional().nullable())
    .optional(),
  period_end_year: z
    .preprocess(toNum, z.number().int().optional().nullable())
    .optional(),
  unesco_inscription_year: z
    .preprocess(toNum, z.number().int().optional().nullable())
    .optional(),
  status: z.enum(['draft', 'review', 'published', 'archived', 'rejected']),
  tags: z.string().optional(),
});

function toNum(v: unknown): number | null | undefined {
  if (v === '' || v === null || v === undefined) return null;
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : null;
}

type FormValues = z.infer<typeof schema>;

const STATUS_OPTIONS: readonly { value: HeritageStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'review', label: 'Review' },
  { value: 'published', label: 'Published' },
  { value: 'archived', label: 'Archived' },
  { value: 'rejected', label: 'Rejected' },
];

const NONE = '__none__';

export function HeritageForm({
  mode,
  initial,
  kindOptions,
  countryOptions,
}: HeritageFormProps): JSX.Element {
  const [name, setName] = useState<Record<string, string>>(initial?.name ?? {});
  const [summary, setSummary] = useState<Record<string, string>>(
    initial?.summary_md ?? {},
  );
  const [description, setDescription] = useState<Record<string, string>>(
    initial?.description_md ?? {},
  );
  const [pending, startTransition] = useTransition();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      kind_slug: initial?.kind_slug ?? '',
      country_code: initial?.country_code ?? '',
      latitude: initial?.latitude == null ? null : Number(initial.latitude),
      longitude: initial?.longitude == null ? null : Number(initial.longitude),
      period_start_year: initial?.period_start_year ?? null,
      period_end_year: initial?.period_end_year ?? null,
      unesco_inscription_year: initial?.unesco_inscription_year ?? null,
      status: initial?.status ?? 'draft',
      tags: initial?.tags.join(', ') ?? '',
    },
  });

  function onSubmit(values: FormValues): void {
    const filteredName = Object.fromEntries(
      Object.entries(name).filter(([, v]) => v.trim()),
    );
    if (Object.keys(filteredName).length === 0) {
      form.setError('kind_slug', { message: 'At least one localised name is required.' });
      toast.error('Provide at least one name translation.');
      return;
    }
    const payload = {
      kind_slug: values.kind_slug,
      name: filteredName,
      summary_md: Object.fromEntries(
        Object.entries(summary).filter(([, v]) => v.trim()),
      ),
      description_md: Object.fromEntries(
        Object.entries(description).filter(([, v]) => v.trim()),
      ),
      tags: values.tags
        ? values.tags
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean)
        : [],
      country_code:
        values.country_code && values.country_code !== NONE
          ? values.country_code
          : undefined,
      latitude: values.latitude ?? null,
      longitude: values.longitude ?? null,
      period_start_year: values.period_start_year ?? null,
      period_end_year: values.period_end_year ?? null,
      unesco_inscription_year: values.unesco_inscription_year ?? null,
      status: values.status,
    };
    startTransition(async () => {
      const result =
        mode === 'create'
          ? await createHeritageAction(payload)
          : await patchHeritageAction(initial!.pub_id, payload);
      if (!result.ok) toast.error(result.message ?? 'Save failed');
      else toast.success('Saved');
    });
  }

  return (
    <form className="grid gap-4 lg:grid-cols-2" onSubmit={form.handleSubmit(onSubmit)}>
      <Card>
        <CardHeader>
          <CardTitle>Core fields</CardTitle>
          <CardDescription>
            Required: at least one localised name + kind.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="kind_slug">Kind</Label>
            <Controller
              control={form.control}
              name="kind_slug"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="kind_slug">
                    <SelectValue placeholder="Select a kind" />
                  </SelectTrigger>
                  <SelectContent>
                    {kindOptions.map((k) => (
                      <SelectItem key={k.value} value={k.value}>
                        {k.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {form.formState.errors.kind_slug ? (
              <p className="text-sm text-destructive">
                {form.formState.errors.kind_slug.message}
              </p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label>Name (per language)</Label>
            <LocaleTextInput value={name} onChange={setName} placeholder="Registan" />
          </div>
          <div className="space-y-2">
            <Label>Summary</Label>
            <LocaleTextInput
              value={summary}
              onChange={setSummary}
              multiline
              placeholder="Short markdown summary"
            />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <LocaleTextInput
              value={description}
              onChange={setDescription}
              multiline
              placeholder="Full markdown description"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tags">Tags (comma separated)</Label>
            <Input id="tags" {...form.register('tags')} placeholder="silk-road, unesco" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Geography &amp; period</CardTitle>
          <CardDescription>Coordinates and historical span.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="country_code">Country</Label>
            <Controller
              control={form.control}
              name="country_code"
              render={({ field }) => (
                <Select
                  value={field.value || NONE}
                  onValueChange={(v) => field.onChange(v === NONE ? '' : v)}
                >
                  <SelectTrigger id="country_code">
                    <SelectValue placeholder="Select country" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>—</SelectItem>
                    {countryOptions.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="latitude">Latitude</Label>
              <Input
                id="latitude"
                type="number"
                step="0.000001"
                {...form.register('latitude')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="longitude">Longitude</Label>
              <Input
                id="longitude"
                type="number"
                step="0.000001"
                {...form.register('longitude')}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="period_start_year">Start year</Label>
              <Input
                id="period_start_year"
                type="number"
                {...form.register('period_start_year')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="period_end_year">End year</Label>
              <Input
                id="period_end_year"
                type="number"
                {...form.register('period_end_year')}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="unesco_inscription_year">UNESCO inscription year</Label>
            <Input
              id="unesco_inscription_year"
              type="number"
              {...form.register('unesco_inscription_year')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Controller
              control={form.control}
              name="status"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>
        </CardContent>
      </Card>

      <div className="lg:col-span-2">
        <Button type="submit" disabled={pending}>
          {mode === 'create' ? 'Create heritage' : 'Save changes'}
        </Button>
      </div>
    </form>
  );
}
