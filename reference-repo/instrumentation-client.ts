import posthog from "posthog-js"
import * as Sentry from "@sentry/nextjs";

// Only initialize PostHog in production
if (process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
    api_host: "/ingest",
    ui_host: "https://eu.posthog.com",
    // defaults "2025-05-24" enables history_change pageview tracking
    // — no custom PostHogPageView component needed
    defaults: "2025-05-24",
    capture_exceptions: true,
    capture_dead_clicks: true,
    capture_heatmaps: true,
    session_recording: {
      maskAllInputs: true,
    },
    capture_performance: true,
  });
}

// Export onRouterTransitionStart hook for Sentry navigation instrumentation
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
