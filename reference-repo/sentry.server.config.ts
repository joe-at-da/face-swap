import * as Sentry from "@sentry/nextjs";

/**
 * Sentry/Glitchtip Server Configuration
 * Optimized for SELF-HOSTED deployment on Coolify (long-running Node.js server)
 * NOT serverless - no need for aggressive flushing
 */
Sentry.init({
  dsn: process.env.GLITCHTIP_DSN,
  
  // Performance Monitoring
  // For self-hosted long-running servers, sample a percentage to avoid overwhelming GlitchTip
  // Adjust based on your traffic - 0.1 = 10%, 0.5 = 50%, 1.0 = 100%
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.25 : 1.0,
  
  // Debug mode for development - disable verbose logging
  debug: false,
  
  // Set environment
  environment: process.env.NODE_ENV,
  
  // Release version for tracking deployments (set via Coolify environment variable)
  release: process.env.NEXT_PUBLIC_APP_VERSION || process.env.GIT_COMMIT_SHA,
  
  // Server name for identifying which instance reported the error
  serverName: process.env.HOSTNAME || process.env.COOLIFY_CONTAINER_NAME || 'nextjs-server',
  
  // Enhanced integrations for server-side error capture and performance monitoring
  integrations: [
    // Capture console methods on server
    // console.error → captured as errors
    // console.log, console.warn, console.info → captured as breadcrumbs
    Sentry.captureConsoleIntegration({
      levels: ['error'],
    }),
    
    // HTTP request tracing for API routes and outgoing requests
    Sentry.httpIntegration(),
    
    Sentry.requestDataIntegration({
      include: {
        cookies: false,
        data: false,
        headers: false,
        ip: false,
        query_string: true,
        url: true,
      },
    }),
    
    // Node.js-specific integrations
    Sentry.onUnhandledRejectionIntegration({
      mode: 'strict',
    }),
    
    // Context lines for better stack traces
    Sentry.contextLinesIntegration(),
    
    Sentry.localVariablesIntegration({
      captureAllExceptions: false,
    }),
  ],
  
  attachStacktrace: true,

  // Filter out known non-critical server errors
  beforeSend(event, hint) {
    if (event.exception) {
      const error = hint.originalException;
      if (error instanceof Error) {
        // Skip Supabase connection warnings during development
        if (error.message?.includes('SUPABASE_URL') || error.message?.includes('SUPABASE_ANON_KEY')) {
          return null;
        }
        // Skip common development-only errors
        if (process.env.NODE_ENV === 'development' && error.message?.includes('ECONNREFUSED')) {
          return null;
        }
        // Skip health check related errors (common with Coolify/Docker health checks)
        if (error.message?.includes('health') && error.message?.includes('check')) {
          return null;
        }
      }
    }
    
    // Add additional context to events
    event.tags = {
      ...event.tags,
      runtime: 'nodejs',
      hosting: 'coolify',
      node_version: process.version,
    };
    
    // Add server context
    event.contexts = {
      ...event.contexts,
      server: {
        hostname: process.env.HOSTNAME,
        container: process.env.COOLIFY_CONTAINER_NAME,
        memory_usage: process.memoryUsage(),
        uptime: process.uptime(),
      },
    };
    
    return event;
  },
  
  // Ignore specific errors that are not actionable
  // Note: These match against error.message content
  ignoreErrors: [
    'NEXT_REDIRECT',
    'NEXT_NOT_FOUND',
    'ECONNRESET',
    'socket hang up',
  ],
});

// ============================================
// SELF-HOSTED SERVER SHUTDOWN HANDLING
// ============================================
// Ensure all events are flushed before the server shuts down
// This is important for Coolify deployments where containers are restarted

/**
 * Flush Sentry events and close the client on shutdown.
 * Uses Sentry.close() which flushes events and prevents new events from being sent.
 * Returns a promise that resolves when flush is complete or times out.
 */
const flushAndExit = (signal: string): void => {
  console.info(`[Glitchtip] Received ${signal}, flushing events before shutdown...`);
  
  // Use Sentry.close() for shutdown - it flushes and prevents new events
  // The promise is properly chained to ensure completion before exit
  Sentry.close(5000)
    .then(() => {
      console.info('[Glitchtip] Events flushed successfully');
    })
    .catch((error) => {
      console.error('[Glitchtip] Error flushing events:', error);
    })
    .finally(() => {
      // Let Next.js continue with its graceful shutdown
      // Don't call process.exit() - Next.js handles that
    });
};

// Register shutdown handlers (only once)
if (typeof process !== 'undefined' && !process.env.__SENTRY_SHUTDOWN_REGISTERED__) {
  process.env.__SENTRY_SHUTDOWN_REGISTERED__ = 'true';
  
  // Use process.once to ensure handlers are only registered once
  // The flushAndExit function is synchronous but initiates async work
  // that will complete before Node.js exits due to the event loop
  process.once('SIGTERM', () => flushAndExit('SIGTERM'));
  process.once('SIGINT', () => flushAndExit('SIGINT'));
  
  // Handle graceful exit - flush any remaining events
  process.once('beforeExit', () => {
    Sentry.flush(2000).catch(() => {});
  });
}