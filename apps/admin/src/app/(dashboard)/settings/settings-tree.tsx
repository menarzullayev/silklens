'use client';

import { useMemo, useState, useTransition } from 'react';
import { toast } from 'sonner';
import { EyeOff, Eye, ChevronRight } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import type { SystemSettingOut } from '@/types/api';
import { saveSystemSettingAction } from './actions';

interface SettingsTreeProps {
  readonly settings: readonly SystemSettingOut[];
}

function groupByPrefix(
  settings: readonly SystemSettingOut[],
): ReadonlyMap<string, readonly SystemSettingOut[]> {
  const map = new Map<string, SystemSettingOut[]>();
  for (const s of settings) {
    const prefix = s.key.split('.')[0] ?? 'other';
    if (!map.has(prefix)) map.set(prefix, []);
    (map.get(prefix) as SystemSettingOut[]).push(s);
  }
  return map;
}

export function SettingsTree({ settings }: SettingsTreeProps): JSX.Element {
  const grouped = useMemo(() => groupByPrefix(settings), [settings]);
  const prefixes = useMemo(() => Array.from(grouped.keys()).sort(), [grouped]);
  const initial = prefixes[0] ?? 'all';
  const [active, setActive] = useState(initial);

  if (settings.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          No system settings configured for this tenant yet.
        </CardContent>
      </Card>
    );
  }

  return (
    <Tabs value={active} onValueChange={setActive} className="space-y-4">
      <TabsList className="flex-wrap">
        {prefixes.map((prefix) => (
          <TabsTrigger key={prefix} value={prefix}>
            <ChevronRight className="mr-1 h-3 w-3 opacity-50" />
            {prefix}
            <span className="ml-1 text-xs text-muted-foreground">
              ({grouped.get(prefix)?.length ?? 0})
            </span>
          </TabsTrigger>
        ))}
      </TabsList>
      {prefixes.map((prefix) => (
        <TabsContent key={prefix} value={prefix}>
          <div className="space-y-3">
            {grouped.get(prefix)?.map((s) => (
              <SettingRow key={s.key} setting={s} />
            ))}
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}

interface SettingRowProps {
  readonly setting: SystemSettingOut;
}

function SettingRow({ setting }: SettingRowProps): JSX.Element {
  const [value, setValue] = useState<unknown>(setting.value);
  const [revealed, setRevealed] = useState(false);
  const [pending, start] = useTransition();

  function save(): void {
    start(async () => {
      const result = await saveSystemSettingAction({
        key: setting.key,
        value,
        value_type: setting.value_type,
        scope: setting.scope,
        description: setting.description,
        is_secret: setting.is_secret,
      });
      if (result.ok) toast.success(`${setting.key} saved`);
      else toast.error(result.message ?? 'Save failed');
    });
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono text-sm">{setting.key}</CardTitle>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-xs">
              {setting.value_type}
            </Badge>
            <Badge variant="secondary" className="text-xs capitalize">
              {setting.scope}
            </Badge>
            {setting.is_secret ? <Badge variant="destructive">secret</Badge> : null}
          </div>
        </div>
        {setting.description ? (
          <CardDescription>{setting.description}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-2">
        <Label className="sr-only" htmlFor={`val-${setting.key}`}>
          Value
        </Label>
        {setting.is_secret && !revealed ? (
          <div className="flex items-center gap-2">
            <Input value="••••••••" disabled className="font-mono" />
            <Button
              size="sm"
              variant="outline"
              onClick={() => setRevealed(true)}
            >
              <Eye className="mr-1 h-4 w-4" />
              Reveal
            </Button>
          </div>
        ) : (
          renderEditor(setting, value, setValue, `val-${setting.key}`)
        )}
        <div className="flex items-center justify-between">
          {setting.is_secret && revealed ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setRevealed(false)}
              className="text-xs"
            >
              <EyeOff className="mr-1 h-3 w-3" /> Hide
            </Button>
          ) : (
            <span />
          )}
          <Button size="sm" onClick={save} disabled={pending}>
            Save
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function renderEditor(
  setting: SystemSettingOut,
  value: unknown,
  setValue: (v: unknown) => void,
  id: string,
): JSX.Element {
  switch (setting.value_type) {
    case 'bool':
      return (
        <div className="flex items-center gap-2">
          <Switch
            id={id}
            checked={Boolean(value)}
            onCheckedChange={(checked) => setValue(checked)}
          />
          <span className="text-sm text-muted-foreground">
            {value ? 'enabled' : 'disabled'}
          </span>
        </div>
      );
    case 'int':
    case 'float':
    case 'duration':
      return (
        <Input
          id={id}
          type="number"
          value={value === null || value === undefined ? '' : String(value)}
          onChange={(e) => {
            const raw = e.target.value;
            setValue(
              raw === ''
                ? null
                : setting.value_type === 'int'
                  ? parseInt(raw, 10)
                  : parseFloat(raw),
            );
          }}
          className="font-mono"
        />
      );
    case 'color':
      return (
        <div className="flex items-center gap-2">
          <Input
            id={id}
            value={typeof value === 'string' ? value : ''}
            onChange={(e) => setValue(e.target.value)}
            className="font-mono"
          />
          <input
            type="color"
            value={typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value) ? value : '#000000'}
            onChange={(e) => setValue(e.target.value)}
            className="h-10 w-12 cursor-pointer rounded-md border"
            aria-label="Color swatch"
          />
        </div>
      );
    case 'json':
      return (
        <Textarea
          id={id}
          value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
          onChange={(e) => {
            try {
              setValue(JSON.parse(e.target.value));
            } catch {
              setValue(e.target.value);
            }
          }}
          rows={6}
          className="font-mono text-xs"
        />
      );
    case 'url':
      return (
        <Input
          id={id}
          type="url"
          value={typeof value === 'string' ? value : ''}
          onChange={(e) => setValue(e.target.value)}
          className="font-mono"
        />
      );
    default:
      return (
        <Input
          id={id}
          value={typeof value === 'string' ? value : value == null ? '' : String(value)}
          onChange={(e) => setValue(e.target.value)}
        />
      );
  }
}
