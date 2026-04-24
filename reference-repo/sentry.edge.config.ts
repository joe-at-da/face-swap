import * as Sentry from "@sentry/nextjs";

/**
 * Sentry/Glitchtip Edge Runtime Configuration
 * Used for Next.js Proxy (even on self-hosted Coolify deployments)
 *
 * Note: Even when self-hosting on Coolify, Next.js proxy runs in a minimal
 * runtime with limited Node.js APIs. This config is only used if you have proxy.
 *
 * IMPORTANT: Edge runtime can only access NEXT_PUBLIC_ prefixed environment variables
 * because it runs in a restricted environment similar to the browser.
 */
Sentry.init({
  // Must use NEXT_PUBLIC_ prefix for edge runtime to access the DSN
  dsn: process.env.NEXT_PUBLIC_GLITCHTIP_DSN,

  // Performance Monitoring
  // Lower sample rate for proxy since it runs on every request
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Debug mode
  debug: false,

  // Set environment
  environment: process.env.NODE_ENV,

  // Release version - must use NEXT_PUBLIC_ prefix for edge runtime
  release:
    process.env.NEXT_PUBLIC_APP_VERSION ||
    process.env.NEXT_PUBLIC_GIT_COMMIT_SHA,

  // Edge runtime integrations (limited due to edge constraints)
  integrations: [
    // Capture console methods on edge runtime
    Sentry.captureConsoleIntegration({
      levels: ["error"],
    }),

    // Wintercg fetch integration for edge runtime
    Sentry.winterCGFetchIntegration(),
  ],

  // Maximum breadcrumbs (keep lower for edge due to memory constraints)
  maxBreadcrumbs: 50,

  // Add breadcrumbs for better debugging context
  beforeBreadcrumb(breadcrumb) {
    if (breadcrumb.category === "console") {
      breadcrumb.data = {
        ...breadcrumb.data,
        timestamp: new Date().toISOString(),
        runtime: "edge",
      };
    }
    return breadcrumb;
  },

  // Filter out edge-specific non-critical errors
  beforeSend(event, hint) {
    if (event.exception) {
      const error = hint.originalException;
      if (error instanceof Error) {
        // Skip edge runtime API limitations
        if (error.message?.includes("not supported in Edge Runtime")) {
          return null;
        }
        // Skip Next.js internal redirect errors
        if (
          error.message?.includes("NEXT_REDIRECT") ||
          error.message?.includes("NEXT_NOT_FOUND")
        ) {
          return null;
        }
      }
    }

    // Add additional context to events
    event.tags = {
      ...event.tags,
      runtime: "edge",
      hosting: "coolify",
    };

    return event;
  },

  // Ignore specific errors
  ignoreErrors: [
    "NEXT_REDIRECT",
    "NEXT_NOT_FOUND",
    "not supported in Edge Runtime",
  ],
});
