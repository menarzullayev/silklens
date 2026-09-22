'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';

import { cn } from '@/lib/utils';

interface BreadcrumbsProps {
  readonly className?: string;
}

/** Derives breadcrumb segments from the current pathname. SSR-safe. */
export function Breadcrumbs({ className }: BreadcrumbsProps): JSX.Element | null {
  const pathname = usePathname();
  const parts = pathname.split('/').filter(Boolean);
  if (parts.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center gap-1 text-sm text-muted-foreground', className)}
    >
      <Link href="/dashboard" className="hover:text-foreground">
        Home
      </Link>
      {parts.map((segment, index) => {
        const href = `/${parts.slice(0, index + 1).join('/')}`;
        const isLast = index === parts.length - 1;
        return (
          <span key={href} className="flex items-center gap-1">
            <ChevronRight className="h-3 w-3" aria-hidden />
            {isLast ? (
              <span className="font-medium text-foreground capitalize">{segment}</span>
            ) : (
              <Link href={href} className="capitalize hover:text-foreground">
                {segment}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
