import { ShieldOff } from 'lucide-react';
import { getTranslations } from 'next-intl/server';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Default unauthorised-state UI. Render it as the `fallback` for
 * `<PermissionGuard />` when a section is permission-gated.
 */
export async function AccessDenied(): Promise<JSX.Element> {
  const t = await getTranslations('rbac');
  return (
    <Card className="mx-auto mt-20 max-w-md border-dashed">
      <CardHeader className="items-center text-center">
        <ShieldOff className="mb-2 h-10 w-10 text-muted-foreground" aria-hidden />
        <CardTitle>{t('denied')}</CardTitle>
      </CardHeader>
      <CardContent className="text-center text-sm text-muted-foreground">
        {t('deniedSubtitle')}
      </CardContent>
    </Card>
  );
}
