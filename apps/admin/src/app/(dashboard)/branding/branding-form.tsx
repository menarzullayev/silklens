'use client';

import { useForm } from 'react-hook-form';
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
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

/**
 * Zod schema mirrors `tenant_branding` from architecture §06.3.1. Keep these
 * column names in sync with the table so OpenAPI/api types are a drop-in
 * replacement when the backend ships.
 */
const brandingSchema = z.object({
  app_name: z.string().min(2).max(80),
  logo_url: z.string().url().optional().or(z.literal('')),
  primary_color: z
    .string()
    .regex(HEX_COLOR_RE, 'Use a 6-digit hex color (e.g. #1e3a8a)'),
  splash_image: z.string().url().optional().or(z.literal('')),
});

type BrandingValues = z.infer<typeof brandingSchema>;

interface BrandingFormProps {
  readonly labels: {
    readonly appName: string;
    readonly logoUrl: string;
    readonly primaryColor: string;
    readonly splashImage: string;
    readonly saved: string;
  };
}

export function BrandingForm({ labels }: BrandingFormProps): JSX.Element {
  const form = useForm<BrandingValues>({
    resolver: zodResolver(brandingSchema),
    defaultValues: {
      app_name: 'SilkLens',
      logo_url: '',
      primary_color: '#1e3a8a',
      splash_image: '',
    },
  });

  function onSubmit(values: BrandingValues): void {
    // TODO(monetization): POST to /tenants/{id}/branding once the
    // tenant-branding endpoint exists. For now we just keep the form's
    // internal state and confirm with a toast.
    toast.success(labels.saved, {
      description: `app_name="${values.app_name}", primary_color="${values.primary_color}"`,
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tenant brand</CardTitle>
        <CardDescription>
          These values map 1:1 onto the <code>tenant_branding</code> row that
          the mobile + web apps load at startup (Project-Decisions §50).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form className="space-y-6" onSubmit={form.handleSubmit(onSubmit)}>
            <FormField
              control={form.control}
              name="app_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{labels.appName}</FormLabel>
                  <FormControl>
                    <Input placeholder="SilkLens" {...field} />
                  </FormControl>
                  <FormDescription>
                    Localised brand name shown in store listings and the app
                    chrome.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="logo_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{labels.logoUrl}</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="https://cdn.silklens.app/logos/light.svg"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="primary_color"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{labels.primaryColor}</FormLabel>
                  <FormControl>
                    <div className="flex items-center gap-3">
                      <Input className="font-mono" {...field} />
                      <span
                        aria-hidden
                        className="h-8 w-8 rounded-md border"
                        style={{
                          backgroundColor: HEX_COLOR_RE.test(field.value)
                            ? field.value
                            : 'transparent',
                        }}
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="splash_image"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{labels.splashImage}</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="https://cdn.silklens.app/splash/uz.webp"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={form.formState.isSubmitting}>
              Save draft
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
