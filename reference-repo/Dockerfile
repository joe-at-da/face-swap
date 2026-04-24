# =============================================================================
# Multi-stage Dockerfile for Next.js 16 with Supabase Migration Support
# =============================================================================
# Production-ready build with automatic database migrations using Supabase CLI
# Optimized for Coolify deployment with minimal image size
#
# Requirements:
#   - next.config.js must have: output: 'standalone'
#   - Environment variable DIRECT_URL for database migrations
#
# Supports: npm, yarn, pnpm, and bun package managers
# =============================================================================

# =============================================================================
# Stage 1: Dependencies
# =============================================================================
FROM node:22-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files for better caching
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* bun.lock* ./

# Install dependencies based on lockfile present
RUN \
  if [ -f bun.lock ]; then npm install -g bun && bun install --frozen-lockfile; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i --frozen-lockfile; \
  elif [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  else echo "No lockfile found." && exit 1; \
  fi

# Install Playwright browsers (needed for parliament scraping scripts)
RUN npx playwright install chromium

# =============================================================================
# Stage 2: Builder
# =============================================================================
FROM node:22-alpine AS builder
WORKDIR /app

# Build-time arguments - use placeholders for NEXT_PUBLIC_* (replaced at runtime)
# Coolify's SERVICE_FQDN_* variables are only available at runtime, not build time.
# Placeholders get baked into JS, then replaced by docker-entrypoint.sh at container startup.
# This supports both main deployments AND PR preview deployments with dynamic URLs.
#
# IMPORTANT: We use _BUILD_PLACEHOLDER_* names (not NEXT_PUBLIC_*) because Coolify
# automatically passes all environment variables as --build-arg, which would override
# our placeholder defaults. Using different names ensures placeholders are preserved.
ARG _BUILD_PLACEHOLDER_SUPABASE_URL=__NEXT_PUBLIC_SUPABASE_URL_PLACEHOLDER__
ARG _BUILD_PLACEHOLDER_SUPABASE_ANON_KEY=__NEXT_PUBLIC_SUPABASE_ANON_KEY_PLACEHOLDER__
ARG _BUILD_PLACEHOLDER_FRONTEND_URL=__NEXT_PUBLIC_FRONTEND_URL_PLACEHOLDER__
ARG SUPABASE_URL
ARG SUPABASE_SERVICE_KEY

# Convert to ENV for Next.js build
# The NEXT_PUBLIC_* values will be placeholders that get replaced at container startup
ENV NEXT_PUBLIC_SUPABASE_URL=${_BUILD_PLACEHOLDER_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${_BUILD_PLACEHOLDER_SUPABASE_ANON_KEY}
ENV NEXT_PUBLIC_FRONTEND_URL=${_BUILD_PLACEHOLDER_FRONTEND_URL}
ENV SUPABASE_URL=${SUPABASE_URL}
ENV SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Disable Next.js telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Force production mode for build — Coolify injects NODE_ENV=development as a
# build-arg which breaks Next.js static prerendering (React dev bundles don't
# support useContext during SSR prerender). ENV overrides the injected ARG.
ENV NODE_ENV=production

# Build using the same package manager that installed dependencies
RUN \
  if [ -f bun.lock ]; then npm install -g bun && bun run build; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm run build; \
  elif [ -f yarn.lock ]; then yarn build; \
  elif [ -f package-lock.json ]; then npm run build; \
  else npm run build; \
  fi

# Ensure supabase folder exists (even if empty) for COPY in runner stage
RUN mkdir -p supabase

# =============================================================================
# Stage 3: Production Runner
# =============================================================================
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# Tell Playwright to use system Chromium instead of downloaded browser
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Install runtime dependencies
# - postgresql-client: for pg_isready health check
# - Chromium dependencies: for Playwright browser automation (parliament scraping)
RUN apk add --no-cache \
    postgresql-client \
    chromium \
    curl \
    aws-cli \
    bash \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    ffmpeg

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application (standalone output)
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy Supabase migrations folder for runtime migrations
COPY --from=builder /app/supabase ./supabase

# Copy entrypoint script
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Copy backup script for Coolify scheduled tasks
COPY coolify-backup-config.sh ./
RUN chmod +x coolify-backup-config.sh

# Switch to non-root user
USER nextjs

# Expose port 3001 (to avoid conflict with Supabase Studio on 3000)
EXPOSE 3001
ENV PORT=3001
ENV HOSTNAME="0.0.0.0"

# Use entrypoint to run migrations before starting
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["node", "server.js"]
