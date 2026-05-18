'use client';

import { Building2, Check, ChevronsUpDown } from 'lucide-react';
import { useTransition } from 'react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { setActiveTenant } from '@/app/(dashboard)/_actions';
import type { TenantDescriptor } from '@/lib/tenant';

interface TenantSwitcherProps {
  readonly tenants: readonly TenantDescriptor[];
  readonly activeTenantId: string;
}

export function TenantSwitcher({
  tenants,
  activeTenantId,
}: TenantSwitcherProps): JSX.Element {
  const [pending, startTransition] = useTransition();
  const active = tenants.find((t) => t.id === activeTenantId) ?? tenants[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="h-9 justify-between gap-2"
          disabled={pending}
        >
          <Building2 className="h-4 w-4 text-muted-foreground" aria-hidden />
          <span className="max-w-[10rem] truncate">
            {active?.displayName ?? 'Select tenant'}
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>Switch tenant</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {tenants.map((tenant) => (
          <DropdownMenuItem
            key={tenant.id}
            onSelect={() => {
              startTransition(async () => {
                await setActiveTenant(tenant.id);
              });
            }}
          >
            <span className="flex-1 truncate">{tenant.displayName}</span>
            {tenant.id === activeTenantId ? (
              <Check className="h-4 w-4 text-primary" aria-hidden />
            ) : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
