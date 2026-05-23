'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import {
  BarChart3,
  Box,
  Building2,
  Cog,
  CreditCard,
  Flag,
  Globe,
  Image as ImageIcon,
  Languages,
  LayoutDashboard,
  Phone,
  ScanFace,
  ShieldCheck,
  Sparkles,
  Tag,
  Users,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { PERMISSIONS, type Permission } from '@/lib/rbac/permissions';

interface NavLink {
  readonly href: string;
  readonly labelKey: keyof IntlMessages['nav'];
  readonly icon: typeof LayoutDashboard;
  readonly permission: Permission;
}

const NAV_LINKS: readonly NavLink[] = [
  { href: '/dashboard', labelKey: 'overview', icon: LayoutDashboard, permission: PERMISSIONS.ANALYTICS_READ },
  { href: '/heritage', labelKey: 'heritage', icon: Box, permission: PERMISSIONS.HERITAGE_READ },
  { href: '/users', labelKey: 'users', icon: Users, permission: PERMISSIONS.USERS_READ },
  { href: '/moderation', labelKey: 'moderation', icon: ShieldCheck, permission: PERMISSIONS.MODERATION_READ },
  { href: '/ai-models', labelKey: 'aiModels', icon: Sparkles, permission: PERMISSIONS.AI_MODELS_READ },
  { href: '/monetization', labelKey: 'monetization', icon: CreditCard, permission: PERMISSIONS.MONETIZATION_READ },
  { href: '/tenants', labelKey: 'tenants', icon: Building2, permission: PERMISSIONS.TENANTS_MANAGE },
  { href: '/branding', labelKey: 'branding', icon: ImageIcon, permission: PERMISSIONS.BRANDING_MANAGE },
  { href: '/feature-flags', labelKey: 'featureFlags', icon: Flag, permission: PERMISSIONS.SETTINGS_MANAGE },
  { href: '/analytics', labelKey: 'analytics', icon: BarChart3, permission: PERMISSIONS.ANALYTICS_READ },
  // SILK-0158: Emergency contacts directory
  { href: '/emergency', labelKey: 'emergency', icon: Phone, permission: PERMISSIONS.SETTINGS_MANAGE },
  // SILK-0159: Cultural tips for travellers
  { href: '/cultural-tips', labelKey: 'culturalTips', icon: Globe, permission: PERMISSIONS.SETTINGS_MANAGE },
  // SILK-0160: Government information
  { href: '/government', labelKey: 'government', icon: Building2, permission: PERMISSIONS.SETTINGS_MANAGE },
  // SILK-0161: Coupon management
  { href: '/billing/coupons', labelKey: 'coupons', icon: Tag, permission: PERMISSIONS.MONETIZATION_READ },
  { href: '/settings', labelKey: 'settings', icon: Cog, permission: PERMISSIONS.SETTINGS_MANAGE },
  // SILK-0166: Language registry
  { href: '/settings/languages', labelKey: 'languages', icon: Languages, permission: PERMISSIONS.SETTINGS_MANAGE },
];

interface AppSidebarProps {
  readonly permissions: readonly string[];
}

/** Minimal next-intl message-tree shape used for type-safe label keys. */
interface IntlMessages {
  nav: Record<
    | 'overview'
    | 'heritage'
    | 'users'
    | 'moderation'
    | 'aiModels'
    | 'monetization'
    | 'tenants'
    | 'branding'
    | 'featureFlags'
    | 'analytics'
    | 'settings'
    | 'emergency'
    | 'culturalTips'
    | 'government'
    | 'coupons'
    | 'languages',
    string
  >;
}

export function AppSidebar({ permissions }: AppSidebarProps): JSX.Element {
  const pathname = usePathname();
  const t = useTranslations('nav');
  const tCommon = useTranslations('common');
  const granted = new Set(permissions);

  return (
    <aside className="hidden h-screen w-64 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground md:flex">
      <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
        <ScanFace className="h-6 w-6 text-primary" aria-hidden />
        <span className="font-semibold tracking-tight">{tCommon('appName')}</span>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Primary">
        {NAV_LINKS.filter((link) => granted.has(link.permission)).map((link) => {
          const Icon = link.icon;
          const isActive =
            pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent/60',
              )}
            >
              <Icon className="h-4 w-4" aria-hidden />
              <span>{t(link.labelKey)}</span>
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-sidebar-border p-4 text-xs text-muted-foreground">
        v0.1.0 · skeleton
      </div>
    </aside>
  );
}
