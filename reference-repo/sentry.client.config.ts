import * as Sentry from "@sentry/nextjs";

/**
 * Sentry/Glitchtip Client Configuration
 * Optimized for SELF-HOSTED deployment on Coolify
 */
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_GLITCHTIP_DSN,
  
  // Performance Monitoring
  // For self-hosted, sample a percentage to reduce data volume
  // Adjust based on your traffic - 0.1 = 10%, 0.5 = 50%, 1.0 = 100%
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.25 : 1.0,
  
  // Session Replay - DISABLED for GlitchTip
  // GlitchTip doesn't support Sentry's session replay feature
  // Set to 0 to avoid sending unsupported data and reduce bandwidth
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,
  
  // Debug mode for development
  debug: false,
  
  // Set environment
  environment: process.env.NODE_ENV,
  
  // Release version for tracking deployments
  release: process.env.NEXT_PUBLIC_APP_VERSION || process.env.NEXT_PUBLIC_GIT_COMMIT_SHA,
  
  // Enhanced integrations for error capture and performance monitoring
  integrations: [
    Sentry.browserTracingIntegration({
      enableInp: true,
    }),
    
    // Capture console methods
    // console.error → captured as errors
    // console.log, console.warn, console.info → captured as breadcrumbs
    Sentry.captureConsoleIntegration({
      levels: ['error'],
    }),
    
    Sentry.httpClientIntegration(),
  ],

  // Filter out known non-critical errors
  beforeSend(event, hint) {
    if (event.exception) {
      const error = hint.originalException;
      if (error instanceof Error) {
        // Skip common browser extension errors
        if (error.message?.includes('Extension')) {
          return null;
        }
        // Skip ResizeObserver loop limit errors (browser quirk)
        if (error.message?.includes('ResizeObserver loop')) {
          return null;
        }
        // Skip cancelled navigation errors
        if (error.message?.includes('cancelled') || error.message?.includes('aborted')) {
          return null;
        }
        // Skip React 19 minified hydration errors (#418, #422, #423)
        if (/Minified React error #(418|422|423)/.test(error.message ?? '')) {
          return null;
        }
      }
    }
    
    // Add additional context to events
    event.tags = {
      ...event.tags,
      client_type: 'browser',
      runtime: 'client',
      hosting: 'coolify',
    };
    
    return event;
  },
  
  // Deny third-party script errors (browser extensions, analytics scripts)
  denyUrls: [
    /^chrome-extension:\/\//,
    /^moz-extension:\/\//,
    /^safari-extension:\/\//,
    /^https?:\/\/www\.google-analytics\.com/,
    /^https?:\/\/www\.googletagmanager\.com/,
  ],

  // Configure allowed URLs for your self-hosted domain
  // Update these with your actual production domain(s)
  allowUrls: [
    // Local development
    /^http:\/\/localhost/,
    /^http:\/\/127\.0\.0\.1/,
    // Self-hosted domains (update these!)
    /^https:\/\/.*\.veedoo\.dev/,
    /^https:\/\/thempai\./,
  ],
  
  // Ignore specific errors that are not actionable
  ignoreErrors: [
    // Network errors during navigation
    'Network request failed',
    'Load failed',
    'Failed to fetch',
    // React hydration warnings
    'Hydration failed',
    'There was an error while hydrating',
    // Chunk loading errors (deployment-related)
    'Loading chunk',
    'ChunkLoadError',
    // Service worker errors
    'ServiceWorker',
  ],
});