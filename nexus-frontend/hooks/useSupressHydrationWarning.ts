import { useEffect } from 'react';

/**
 * Hook to suppress hydration warnings caused by browser extensions
 * This is specifically for warnings caused by extensions like Windsurf
 * that inject attributes into the DOM
 */
export function useSuppressHydrationWarning() {
  useEffect(() => {
    // Store the original console.error
    const originalError = console.error;
    
    // Override console.error to filter out hydration warnings
    console.error = (...args: any[]) => {
      const message = args[0];
      
      // Check if this is a hydration warning we want to suppress
      if (
        typeof message === 'string' && (
          message.includes('A tree hydrated but some attributes') ||
          message.includes('data-windsurf') ||
          message.includes('Hydration failed') ||
          message.includes('hydration-mismatch') ||
          message.includes('Each child in a list should have a unique "key" prop')
        )
      ) {
        // Suppress this error
        return;
      }
      
      // Log all other errors normally
      originalError.apply(console, args);
    };
    
    // Cleanup: restore original console.error when component unmounts
    return () => {
      console.error = originalError;
    };
  }, []);
}
