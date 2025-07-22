import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Suppress hydration warnings caused by browser extensions
  onRecoverableError: (error: Error) => {
    // Suppress hydration errors caused by browser extensions
    if (
      error.message.includes('Hydration failed') ||
      error.message.includes('hydrated but some attributes') ||
      error.message.includes('data-windsurf')
    ) {
      return; // Suppress these specific errors
    }
    // Log other errors normally
    console.error('Recoverable error:', error);
  },
  
  // Additional React configuration
  reactStrictMode: true,
  
  // Suppress hydration warnings in development
  ...(process.env.NODE_ENV === 'development' && {
    webpack: (config: any) => {
      config.infrastructureLogging = {
        level: 'error',
      };
      return config;
    },
  }),
};

export default nextConfig;
