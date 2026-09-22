'use client';

import { useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { signInWithCredentialsAction, signInWithProviderAction } from './actions';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, 'Password is required'),
});

type FormValues = z.infer<typeof schema>;

interface LoginFormProps {
  readonly nextPath: string;
  readonly error?: string;
  readonly labels: {
    readonly email: string;
    readonly password: string;
    readonly signIn: string;
    readonly signInWithGoogle: string;
    readonly signInWithApple: string;
    readonly signInWithTelegram: string;
    readonly cancel: string;
  };
}

export function LoginForm({ nextPath, error, labels }: LoginFormProps): JSX.Element {
  const [pending, startTransition] = useTransition();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  });

  function onSubmit(values: FormValues): void {
    startTransition(async () => {
      const result = await signInWithCredentialsAction({
        email: values.email,
        password: values.password,
        nextPath,
      });
      if (!result.ok) toast.error(result.message);
    });
  }

  return (
    <Form {...form}>
      {error ? (
        <p
          role="alert"
          className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{labels.email}</FormLabel>
              <FormControl>
                <Input
                  type="email"
                  autoComplete="email"
                  placeholder="you@silklens.app"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{labels.password}</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="current-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" className="w-full" disabled={pending}>
          {labels.signIn}
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs uppercase text-muted-foreground">
        <Separator className="flex-1" />
        <span>or</span>
        <Separator className="flex-1" />
      </div>

      <div className="space-y-2">
        <form
          action={async () => {
            const result = await signInWithProviderAction('google', nextPath);
            if (result && !result.ok && result.message) toast.error(result.message);
          }}
        >
          <Button type="submit" variant="outline" className="w-full" disabled={pending}>
            {labels.signInWithGoogle}
          </Button>
        </form>
        <form
          action={async () => {
            const result = await signInWithProviderAction('apple', nextPath);
            if (result && !result.ok && result.message) toast.error(result.message);
          }}
        >
          <Button type="submit" variant="outline" className="w-full" disabled={pending}>
            {labels.signInWithApple}
          </Button>
        </form>
        <form
          action={async () => {
            const result = await signInWithProviderAction('telegram', nextPath);
            if (result && !result.ok && result.message) toast.error(result.message);
          }}
        >
          <Button type="submit" variant="outline" className="w-full" disabled={pending}>
            {labels.signInWithTelegram}
          </Button>
        </form>
      </div>
    </Form>
  );
}
