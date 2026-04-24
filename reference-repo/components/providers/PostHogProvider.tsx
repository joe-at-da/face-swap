"use client";

import { PostHogProvider as PHProvider } from "posthog-js/react";
import posthog from "posthog-js";

// PostHog is initialized in instrumentation-client.ts (production only)
// Pageview tracking is handled automatically by PostHog's "history_change" mode
// (enabled via defaults: "2025-05-24" in instrumentation-client.ts)

/**
 * PostHog Provider Component
 * Wraps the application to provide PostHog analytics context
 * PostHog initialization happens in instrumentation-client.ts (production only)
 * Always wraps with PHProvider so usePostHog() returns a consistent client object
 * The client handles disabled state gracefully - calls to capture() are no-ops when not initialized
 */
export function PostHogProvider({ children }: { children: React.ReactNode }) {
  return (
    <PHProvider client={posthog}>
      {children}
    </PHProvider>
  );
}
