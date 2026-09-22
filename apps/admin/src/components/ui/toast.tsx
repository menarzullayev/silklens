'use client';

import { Toaster as SonnerToaster } from 'sonner';
import { useTheme } from 'next-themes';

/**
 * Thin wrapper around `sonner` that wires it to the active next-themes theme.
 * Keep the public surface to `<Toaster />` + `toast(...)` imported from
 * `sonner` directly elsewhere in the app.
 */
export function Toaster(): JSX.Element {
  const { theme } = useTheme();
  return (
    <SonnerToaster
      theme={(theme as 'light' | 'dark' | 'system' | undefined) ?? 'system'}
      position="top-right"
      richColors
      closeButton
    />
  );
}
