#!/bin/sh
set -e

# =============================================================================
# Docker Entrypoint Script for Next.js with Supabase Migrations
# =============================================================================
# This script runs database migrations using Supabase CLI before starting
# the application. It ensures the database is ready and migrations are applied.
#
# Environment Variables Required:
#   - DIRECT_URL: Direct PostgreSQL connection string (not pooled)
#
# Reference: https://supabase.com/docs/reference/cli/supabase-db-push
# =============================================================================

echo "=========================================="
echo "Starting deployment..."
echo "=========================================="

# Wait for database to be ready (max 60 seconds)
if [ -n "$DIRECT_URL" ]; then
    echo "Waiting for database connection..."
    max_attempts=30
    attempt=0

    until pg_isready -d "$DIRECT_URL" > /dev/null 2>&1 || [ $attempt -eq $max_attempts ]; do
        attempt=$((attempt + 1))
        echo "Database not ready, waiting... (attempt $attempt/$max_attempts)"
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        echo "WARNING: Database connection timeout, proceeding anyway..."
    else
        echo "Database is ready!"
    fi
fi

# Run Supabase migrations if supabase folder exists
if [ -d "./supabase/migrations" ]; then
    if [ -z "$DIRECT_URL" ]; then
        echo "WARNING: supabase/migrations folder found but DIRECT_URL is not set."
        echo "Skipping migrations. Set DIRECT_URL to enable database migrations."
    else
        echo "Running Supabase migrations..."

        # Push migrations to the database using Supabase CLI
        # Flags:
        #   --db-url: Direct database connection (not pooled)
        #   --include-all: Include all migrations not found on remote history table
        #   yes |: Auto-confirm prompts for CI/non-interactive environments
        yes | PGSSLMODE=disable npx supabase db push --db-url "$DIRECT_URL" --include-all

        echo "Supabase migrations completed successfully."
    fi
else
    echo "No supabase/migrations folder found, skipping migrations."
fi

# =============================================================================
# Replace NEXT_PUBLIC_* placeholders with runtime environment values
# =============================================================================
# Next.js bakes NEXT_PUBLIC_* variables at build time into BOTH:
#   - Client-side bundles (.next/static/)
#   - Server-side code (.next/server/ and server.js)
# We must replace in ALL locations to prevent React hydration mismatch.
# Since Coolify's SERVICE_FQDN_* variables are only available at runtime,
# we use placeholders during build and replace them at container startup.

echo "=========================================="
echo "Injecting runtime environment variables..."
echo "=========================================="

# Track total replacements for verification
TOTAL_REPLACEMENTS=0

if [ -n "$NEXT_PUBLIC_SUPABASE_URL" ]; then
    echo "  - NEXT_PUBLIC_SUPABASE_URL: $NEXT_PUBLIC_SUPABASE_URL"
    # Count files containing placeholder BEFORE replacement
    COUNT=$(grep -rl "__NEXT_PUBLIC_SUPABASE_URL_PLACEHOLDER__" /app --include="*.js" 2>/dev/null | wc -l || echo "0")
    # Replace in ALL JS files (client + server) to prevent hydration mismatch
    find /app -type f -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_SUPABASE_URL_PLACEHOLDER__|${NEXT_PUBLIC_SUPABASE_URL}|g" {} + 2>/dev/null || true
    echo "    (replaced in $COUNT files)"
    TOTAL_REPLACEMENTS=$((TOTAL_REPLACEMENTS + COUNT))
fi

if [ -n "$NEXT_PUBLIC_SUPABASE_ANON_KEY" ]; then
    echo "  - NEXT_PUBLIC_SUPABASE_ANON_KEY: [set]"
    COUNT=$(grep -rl "__NEXT_PUBLIC_SUPABASE_ANON_KEY_PLACEHOLDER__" /app --include="*.js" 2>/dev/null | wc -l || echo "0")
    find /app -type f -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_SUPABASE_ANON_KEY_PLACEHOLDER__|${NEXT_PUBLIC_SUPABASE_ANON_KEY}|g" {} + 2>/dev/null || true
    echo "    (replaced in $COUNT files)"
    TOTAL_REPLACEMENTS=$((TOTAL_REPLACEMENTS + COUNT))
fi

if [ -n "$NEXT_PUBLIC_FRONTEND_URL" ]; then
    echo "  - NEXT_PUBLIC_FRONTEND_URL: $NEXT_PUBLIC_FRONTEND_URL"
    COUNT=$(grep -rl "__NEXT_PUBLIC_FRONTEND_URL_PLACEHOLDER__" /app --include="*.js" 2>/dev/null | wc -l || echo "0")
    find /app -type f -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_FRONTEND_URL_PLACEHOLDER__|${NEXT_PUBLIC_FRONTEND_URL}|g" {} + 2>/dev/null || true
    echo "    (replaced in $COUNT files)"
    TOTAL_REPLACEMENTS=$((TOTAL_REPLACEMENTS + COUNT))
fi

if [ "$TOTAL_REPLACEMENTS" -eq 0 ]; then
    echo "  WARNING: No placeholder replacements made!"
    echo "  Check that placeholders exist in the build output."
fi

echo "Runtime environment injection complete."

echo "=========================================="
echo "Starting application..."
echo "=========================================="

# Execute the main command (CMD)
exec "$@"
