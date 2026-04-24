import * as Sentry from "@sentry/nextjs";

/**
 * Next.js instrumentation hook
 * This runs once when the Next.js server starts
 * Used to initialize Sentry/Glitchtip for server runtime
 *
 * SELF-HOSTED ON COOLIFY: We primarily use the Node.js runtime.
 * Edge runtime config is kept for proxy compatibility but is rarely used.
 */
export async function register() {
  // Initialize Sentry for Node.js runtime (API routes, Server Components, Server Actions)
  // This is the primary runtime for self-hosted Coolify deployments
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");

    // Log successful initialization in development
    if (process.env.NODE_ENV === "development") {
      console.info("[Glitchtip] Server-side error tracking initialized");
    }
  }

  // Initialize Sentry for Edge runtime (Proxy only)
  // Note: On self-hosted Coolify, this is only used if you have Next.js proxy
  // PostHog client initialization is handled separately via PostHogProvider component
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");

    if (process.env.NODE_ENV === "development") {
      console.info("[Glitchtip] Edge/Proxy error tracking initialized");
    }
  }
}

/**
 * Next.js 15+ onRequestError hook
 * Called automatically for ALL errors in:
 * - API routes
 * - Server Components
 * - Server Actions
 * - Proxy
 * - Page rendering
 *
 * This provides comprehensive error tracking without manual try/catch
 * Uses Sentry.captureException for maximum compatibility with GlitchTip
 */
export async function onRequestError(
  err: Error,
  request: Request,
  context: {
    routerKind: "Pages Router" | "App Router";
    routePath: string;
    routeType: "render" | "route" | "action" | "middleware";
  }
): Promise<void> {
  // Extract additional request context
  const url = new URL(request.url);

  // Safely extract headers (avoiding TypeScript issues with Headers.entries())
  const headers: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    // Skip sensitive headers
    if (!["authorization", "cookie", "x-api-key"].includes(key.toLowerCase())) {
      headers[key] = value;
    }
  });

  // Capture the error with full context using the well-documented captureException
  Sentry.captureException(err, {
    level: "error",
    contexts: {
      nextjs: {
        request_url: request.url,
        router_kind: context.routerKind,
        route_path: context.routePath,
        route_type: context.routeType,
      },
      request: {
        method: request.method,
        url: request.url,
        pathname: url.pathname,
        search: url.search,
        headers: headers,
      },
    },
    tags: {
      runtime: "server",
      router_kind: context.routerKind.replace(" ", "_").toLowerCase(),
      route_type: context.routeType,
      route_path: context.routePath,
      http_method: request.method,
    },
    extra: {
      timestamp: new Date().toISOString(),
    },
  });

  // Note: For self-hosted long-running servers (Coolify), we do NOT flush here.
  // Sentry automatically batches and sends events. Flushing on every error would
  // add up to 2s latency per error response. Events are flushed on server shutdown
  // via SIGTERM/SIGINT handlers in sentry.server.config.ts.
}
