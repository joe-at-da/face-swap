import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  images: {
    dangerouslyAllowLocalIP: true,
    remotePatterns: [
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "55321",
        pathname: "/storage/v1/object/public/**",
      },
      {
        protocol: "https",
        hostname: "fsn1.your-objectstorage.com",
        port: "",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "mp-supabase.veedoo.dev",
        port: "",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.lon1.digitaloceanspaces.com",
        port: "",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.lon1.cdn.digitaloceanspaces.com",
        port: "",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.parliament.uk",
        port: "",
        pathname: "/**",
      },
    ],
    minimumCacheTTL: 86400, // 1 day — controls /_next/image Cache-Control
  },
  // Externalize postgres, import-in-the-middle, and require-in-the-middle for server-side rendering
  serverExternalPackages: [
    "postgres",
    "import-in-the-middle",
    "require-in-the-middle",
    "@remotion/renderer",
    "ffmpeg-static",
  ],

  // Cache and security headers
  async headers() {
    return [
      // Public folder static assets — not content-hashed so avoid immutable
      {
        source: "/:path*.:ext(jpg|jpeg|png|svg|gif|webp|ico|woff|woff2|ttf|eot)",
        headers: [
          {
            key: "Cache-Control",
            value:
              "public, max-age=604800, stale-while-revalidate=86400",
          },
          {
            key: "CDN-Cache-Control",
            value: "public, max-age=2592000",
          },
        ],
      },
      // _next/static assets are content-hashed — safe to use immutable
      // (overrides the shorter cache from the general rule above)
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
          {
            key: "CDN-Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      // Next.js optimized images — CDN header only (browser Cache-Control
      // is set by the image handler via images.minimumCacheTTL)
      {
        source: "/_next/image",
        headers: [
          {
            key: "CDN-Cache-Control",
            value: "public, max-age=604800",
          },
        ],
      },
      // Security headers for all routes
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
      // X-Frame-Options for all routes except /embed (which loads in iframes)
      {
        source: "/((?!embed(?:/|$)).*)",
        headers: [{ key: "X-Frame-Options", value: "DENY" }],
      },
    ];
  },

  // PostHog rewrites to support PostHog API and assets
  async rewrites() {
    return [
      {
        source: "/ingest/static/:path*",
        destination: "https://eu-assets.i.posthog.com/static/:path*",
      },
      {
        source: "/ingest/:path*",
        destination: "https://eu.i.posthog.com/:path*",
      },
    ];
  },

  // Required to support PostHog trailing slash API requests
  skipTrailingSlashRedirect: true,
};

/**
 * Sentry/Glitchtip configuration for SELF-HOSTED deployment on Coolify
 *
 * Key differences from serverless (Vercel) deployment:
 * - Source map uploads are DISABLED (GlitchTip has limited source map support)
 * - No Sentry CLI usage (we're using GlitchTip, not Sentry)
 * - Telemetry is disabled
 *
 * For source maps in self-hosted:
 * - Enable productionBrowserSourceMaps if you want to debug client errors
 * - Source maps will be served alongside your JS files
 * - This slightly increases bundle size but helps debugging
 */
const sentryWebpackPluginOptions = {
  // Suppress all Sentry CLI output
  silent: true,

  // DISABLE source map uploads - GlitchTip doesn't support Sentry's source map API
  // If you're using actual Sentry, you can enable this
  org: undefined,
  project: undefined,
  authToken: undefined,

  // Disable the webpack plugins that upload source maps
  // We're self-hosting with GlitchTip, not using Sentry's cloud
  disableServerWebpackPlugin: true,
  disableClientWebpackPlugin: true,

  // Don't hide source maps - keep them for debugging in self-hosted env
  // Set to true if you want to hide them for security
  hideSourceMaps: process.env.NODE_ENV === "production",

  // Disable telemetry to Sentry (we're using GlitchTip)
  telemetry: false,

  // Webpack configuration for automatic instrumentation
  // Automatically instrument API routes, Server Components, and Server Actions
  // This is useful for self-hosted as it provides automatic error capture
  webpack: {
    autoInstrumentServerFunctions: true,
    autoInstrumentMiddleware: true,
    autoInstrumentAppDirectory: true,
    automaticVercelMonitors: false,
  },

  // Tunnel Sentry events through your own domain to avoid ad blockers
  // Uncomment if you want to proxy events through your server
  // tunnelRoute: "/monitoring",
};

export default withSentryConfig(nextConfig, sentryWebpackPluginOptions);
