import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LOCALES, LOCALE_LABELS } from '@/lib/i18n/config';
import type { HeritageOut } from '@/types/api';

interface Props {
  readonly heritage: HeritageOut;
}

const FIELDS: readonly { key: 'name' | 'summary_md' | 'description_md'; label: string }[] = [
  { key: 'name', label: 'Name' },
  { key: 'summary_md', label: 'Summary' },
  { key: 'description_md', label: 'Description' },
];

export function TranslationsMatrix({ heritage }: Props): JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Translation coverage</CardTitle>
        <CardDescription>
          Read-only matrix of every i18n field across the launch locales. Use
          the Overview tab to edit any cell.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Field</TableHead>
              {LOCALES.map((locale) => (
                <TableHead key={locale}>{LOCALE_LABELS[locale]}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {FIELDS.map((f) => (
              <TableRow key={f.key}>
                <TableCell className="font-medium">{f.label}</TableCell>
                {LOCALES.map((locale) => {
                  const v = heritage[f.key]?.[locale];
                  return (
                    <TableCell
                      key={locale}
                      className="max-w-xs truncate text-xs text-muted-foreground"
                      title={v ?? ''}
                    >
                      {v ? v.slice(0, 80) : '—'}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
