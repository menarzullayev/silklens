'use client';

import { useState, useTransition } from 'react';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { addAliasAction } from '../actions';

const schema = z.object({
  alias: z.string().min(1).max(512),
  language_tag: z.string().min(2).max(32),
  kind: z.enum(['historical', 'colloquial', 'transliteration', 'modern']).default('historical'),
  confidence: z.coerce.number().int().min(0).max(100).default(80),
  source: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface AliasesPanelProps {
  readonly pubId: string;
}

export function AliasesPanel({ pubId }: AliasesPanelProps): JSX.Element {
  const [pending, start] = useTransition();
  const [aliases, setAliases] = useState<readonly FormValues[]>([]);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      alias: '',
      language_tag: 'en',
      kind: 'historical',
      confidence: 80,
      source: '',
    },
  });

  function onSubmit(values: FormValues): void {
    start(async () => {
      const result = await addAliasAction(pubId, {
        alias: values.alias,
        language_tag: values.language_tag,
        kind: values.kind,
        confidence: values.confidence,
        source: values.source ?? null,
      });
      if (result.ok) {
        toast.success('Alias added');
        setAliases((prev) => [values, ...prev]);
        form.reset({
          alias: '',
          language_tag: values.language_tag,
          kind: values.kind,
          confidence: values.confidence,
          source: '',
        });
      } else {
        toast.error(result.message ?? 'Alias create failed');
      }
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Aliases</CardTitle>
        <CardDescription>
          Historical / colloquial / transliterated names for this heritage.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <form
          className="grid gap-3 sm:grid-cols-4"
          onSubmit={form.handleSubmit(onSubmit)}
        >
          <div className="space-y-1 sm:col-span-2">
            <Label htmlFor="alias">Alias</Label>
            <Input id="alias" {...form.register('alias')} placeholder="Maracanda" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="language_tag">Language tag</Label>
            <Input id="language_tag" {...form.register('language_tag')} placeholder="grc" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="confidence">Confidence</Label>
            <Input
              id="confidence"
              type="number"
              {...form.register('confidence')}
              min={0}
              max={100}
            />
          </div>
          <div className="space-y-1 sm:col-span-3">
            <Label htmlFor="source">Source URL or citation</Label>
            <Input
              id="source"
              {...form.register('source')}
              placeholder="Strabo, Geographica XI.11"
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" className="w-full" disabled={pending}>
              Add alias
            </Button>
          </div>
        </form>

        {aliases.length > 0 ? (
          <ul className="divide-y rounded-md border">
            {aliases.map((a, i) => (
              <li key={`${a.alias}-${i}`} className="flex justify-between p-3 text-sm">
                <div>
                  <span className="font-medium">{a.alias}</span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {a.language_tag} · {a.kind}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">{a.confidence}%</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Use the form above to register a new alias.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
