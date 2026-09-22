import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDateTime } from '@/lib/utils';
import type { HeritageRevision } from '@/types/api';

interface Props {
  readonly revisions: readonly HeritageRevision[];
}

export function RevisionsTimeline({ revisions }: Props): JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Revision history</CardTitle>
      </CardHeader>
      <CardContent>
        {revisions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No revisions recorded.</p>
        ) : (
          <ol className="space-y-4">
            {revisions.map((r) => (
              <li
                key={r.id}
                className="relative border-l-2 border-muted pl-4"
              >
                <span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full bg-primary" />
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium">
                    rev {r.revision} · {r.action}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {formatDateTime(r.valid_from)}
                  </Badge>
                </div>
                {r.comment ? (
                  <p className="mt-1 text-sm text-muted-foreground">{r.comment}</p>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
