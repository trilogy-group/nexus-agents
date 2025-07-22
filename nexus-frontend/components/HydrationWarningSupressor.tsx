'use client';

import { useSuppressHydrationWarning } from '@/hooks/useSupressHydrationWarning';

/**
 * Component that suppresses hydration warnings caused by browser extensions
 * This should be included at the root level of the application
 */
export function HydrationWarningSupressor() {
  useSuppressHydrationWarning();
  return null; // This component renders nothing, just runs the hook
}
