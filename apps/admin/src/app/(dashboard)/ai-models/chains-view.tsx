import { ArrowRight } from 'lucide-react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { AiChainOut } from '@/types/api';

interface Props {
  readonly chains: readonly AiChainOut[];
}

function pickName(name: Record<string, string>): string {
  return name.en ?? name.uz ?? Object.values(name)[0] ?? '';
}

export function ChainsView({ chains }: Props): JSX.Element {
  if (chains.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          No fallback chains configured yet.
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="space-y-3">
      {chains.map((chain) => (
        <Card key={chain.slug}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">
                {pickName(chain.name)}{' '}
                <span className="ml-1 font-mono text-xs text-muted-foreground">
                  ({chain.slug})
                </span>
              </CardTitle>
              <Badge variant={chain.is_active ? 'default' : 'outline'}>
                {chain.is_active ? 'active' : 'inactive'}
              </Badge>
            </div>
            <CardDescription className="capitalize">
              {chain.task_type}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="flex flex-wrap items-center gap-2">
              {chain.steps.length === 0 ? (
                <li className="text-sm text-muted-foreground">No steps.</li>
              ) : (
                chain.steps.map((step, idx) => (
                  <li key={`${step.step_order}-${step.model_slug}`} className="flex items-center gap-2">
                    <div className="rounded-md border bg-background px-3 py-2 text-xs">
                      <div className="font-semibold">{step.model_slug}</div>
                      <div className="text-muted-foreground">
                        step {step.step_order}
                        {step.max_latency_ms != null
                          ? ` · ≤${step.max_latency_ms}ms`
                          : ''}
                      </div>
                    </div>
                    {idx < chain.steps.length - 1 ? (
                      <ArrowRight className="h-4 w-4 text-muted-foreground" aria-hidden />
                    ) : null}
                  </li>
                ))
              )}
            </ol>
            <p className="mt-3 text-xs text-muted-foreground">
              Drag-to-reorder editing is read-only here; edit individual model
              priorities via the Models tab.
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
