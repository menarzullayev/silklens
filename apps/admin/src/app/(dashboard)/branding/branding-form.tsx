'use client';

import { useState, useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { ImageOff } from 'lucide-react';

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
import { saveBrandingAction } from './actions';
import type { BrandingOut } from '@/types/api';

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

const schema = z.object({
  logo_url: z.string().url().optional().or(z.literal('')),
  logo_dark_url: z.string().url().optional().or(z.literal('')),
  primary_color: z.string().regex(HEX_COLOR_RE).optional().or(z.literal('')),
  accent_color: z.string().regex(HEX_COLOR_RE).optional().or(z.literal('')),
  splash_url: z.string().url().optional().or(z.literal('')),
  font_family: z.string().optional().or(z.literal('')),
  theme_mode_default: z
    .enum(['light', 'dark', 'system', 'national', 'high_contrast'])
    .default('system'),
});

type FormValues = z.infer<typeof schema>;

const FONT_OPTIONS: readonly string[] = [
  'Inter',
  'Roboto',
  'Open Sans',
  'Noto Sans',
  'Noto Serif',
  'Manrope',
  'Plus Jakarta Sans',
  'Nunito',
  'IBM Plex Sans',
];

interface BrandingFormProps {
  readonly slug: string;
  readonly initial: BrandingOut;
  readonly labels: {
    readonly appName: string;
    readonly logoUrl: string;
    readonly primaryColor: string;
    readonly splashImage: string;
    readonly saved: string;
  };
}

export function BrandingForm({
  slug,
  initial,
  labels,
}: BrandingFormProps): JSX.Element {
  const [appName, setAppName] = useState<Record<string, string>>(
    Object.keys(initial.app_name).length > 0 ? initial.app_name : { en: 'SilkLens' },
  );
  const [pending, start] = useTransition();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      logo_url: initial.logo_url ?? '',
      logo_dark_url: initial.logo_dark_url ?? '',
      primary_color: initial.primary_color ?? '#1e3a8a',
      accent_color: initial.accent_color ?? '#f59e0b',
      splash_url: initial.splash_url ?? '',
      font_family: initial.font_family ?? 'Inter',
      theme_mode_default:
        (initial.theme_mode_default as FormValues['theme_mode_default']) ?? 'system',
    },
  });

  const primary = form.watch('primary_color') || '#1e3a8a';
  const accent = form.watch('accent_color') || '#f59e0b';
  const fontFamily = form.watch('font_family') || 'Inter';
  const logoUrl = form.watch('logo_url');

  function onSubmit(values: FormValues): void {
    const filteredName = Object.fromEntries(
      Object.entries(appName).filter(([, v]) => v.trim()),
    );
    start(async () => {
      const result = await saveBrandingAction(slug, {
        app_name: Object.keys(filteredName).length > 0 ? filteredName : undefined,
        logo_url: values.logo_url || null,
        logo_dark_url: values.logo_dark_url || null,
        primary_color: values.primary_color || null,
        accent_color: values.accent_color || null,
        splash_url: values.splash_url || null,
        font_family: values.font_family || null,
        theme_mode_default: values.theme_mode_default,
        extra: {},
      });
      if (result.ok) toast.success(labels.saved);
      else toast.error(result.message ?? 'Save failed');
    });
  }

  const previewName = appName.en ?? appName.uz ?? Object.values(appName)[0] ?? 'SilkLens';

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Tenant brand</CardTitle>
          <CardDescription>
            These values map 1:1 onto the <code>tenant_branding</code> row that
            the mobile + web apps load at startup.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={form.handleSubmit(onSubmit)}>
            <div className="space-y-2">
              <Label>{labels.appName}</Label>
              <LocaleTextInput value={appName} onChange={setAppName} placeholder="SilkLens" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="logo_url">{labels.logoUrl} (light)</Label>
                <Input
                  id="logo_url"
                  {...form.register('logo_url')}
                  placeholder="https://cdn.silklens.app/logos/light.svg"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="logo_dark_url">Logo URL (dark)</Label>
                <Input
                  id="logo_dark_url"
                  {...form.register('logo_dark_url')}
                  placeholder="https://cdn.silklens.app/logos/dark.svg"
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <ColorPicker
                id="primary_color"
                label={labels.primaryColor}
                value={primary}
                onChange={(v) => form.setValue('primary_color', v, { shouldDirty: true })}
              />
              <ColorPicker
                id="accent_color"
                label="Accent color"
                value={accent}
                onChange={(v) => form.setValue('accent_color', v, { shouldDirty: true })}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="splash_url">{labels.splashImage}</Label>
              <Input
                id="splash_url"
                {...form.register('splash_url')}
                placeholder="https://cdn.silklens.app/splash/uz.webp"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="font_family">Font family</Label>
                <Select
                  value={fontFamily}
                  onValueChange={(v) =>
                    form.setValue('font_family', v, { shouldDirty: true })
                  }
                >
                  <SelectTrigger id="font_family">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {FONT_OPTIONS.map((f) => (
                      <SelectItem key={f} value={f}>
                        {f}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="theme_mode_default">Default theme</Label>
                <Select
                  value={form.watch('theme_mode_default')}
                  onValueChange={(v) =>
                    form.setValue(
                      'theme_mode_default',
                      v as FormValues['theme_mode_default'],
                      { shouldDirty: true },
                    )
                  }
                >
                  <SelectTrigger id="theme_mode_default">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['system', 'light', 'dark', 'national', 'high_contrast'].map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button type="submit" disabled={pending}>
              Save branding
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Live preview</CardTitle>
          <CardDescription>
            Approximate mobile-app chrome with current values.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="mx-auto aspect-[9/16] w-full max-w-[260px] overflow-hidden rounded-2xl border shadow"
            style={{ fontFamily: `'${fontFamily}', system-ui, sans-serif` }}
          >
            <div
              className="flex h-16 items-center gap-2 px-4 text-white"
              style={{ backgroundColor: primary }}
            >
              {logoUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={logoUrl}
                  alt=""
                  className="h-7 w-7 rounded bg-white/10 object-contain p-1"
                />
              ) : (
                <div className="flex h-7 w-7 items-center justify-center rounded bg-white/15">
                  <ImageOff className="h-4 w-4" aria-hidden />
                </div>
              )}
              <span className="text-sm font-semibold">{previewName}</span>
            </div>
            <div className="space-y-3 p-4">
              <div className="h-24 rounded-lg bg-muted" />
              <div className="space-y-1">
                <div className="h-3 w-3/4 rounded bg-muted" />
                <div className="h-3 w-1/2 rounded bg-muted" />
              </div>
              <button
                type="button"
                className="w-full rounded-md py-2 text-xs font-semibold text-white"
                style={{ backgroundColor: accent }}
              >
                Explore heritage
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface ColorPickerProps {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
}

function ColorPicker({ id, label, value, onChange }: ColorPickerProps): JSX.Element {
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex items-center gap-2">
        <Input
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="font-mono"
        />
        <input
          aria-label={`${label} swatch`}
          type="color"
          value={HEX_COLOR_RE.test(value) ? value : '#000000'}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-12 cursor-pointer rounded-md border"
        />
      </div>
    </div>
  );
}
