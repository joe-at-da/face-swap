#!/bin/bash
# =============================================================================
# Auto-configure ports for git worktree based on directory name
# Usage: ./setup-worktree.sh
# =============================================================================
# No arguments needed! The script automatically:
# 1. Hashes the current directory name to get a unique offset (0-998)
# 2. Same directory always gets the same ports (deterministic)
# 3. Creates/updates .env with the calculated ports
# =============================================================================

set -e

# Parse command-line arguments
FORCE=false
LIVE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -l|--live)
            LIVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./setup-worktree.sh [options]"
            echo ""
            echo "Options:"
            echo "  -f, --force    Force full setup even if services are running"
            echo "  -l, --live     Stream Next.js logs after setup (keeps running)"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get the full path for unique port calculation
FULL_PATH=$(pwd)
# Get directory name for display and project naming
DIR_NAME=$(basename "$FULL_PATH")

# Hash the full path to get a number 0-998
# Using cksum for portability, mod 999 for range
OFFSET=$(echo "$FULL_PATH" | cksum | awk '{print $1 % 999}')

# Calculate ports based on offset
NEXTJS_PORT=$((3001 + OFFSET))
KONG_PORT=$((8000 + OFFSET))
POSTGRES_PORT=$((5432 + OFFSET))
POOLER_PORT=$((6543 + OFFSET))
MAILPIT_HTTP_PORT=$((9025 + OFFSET))
MAILPIT_SMTP_PORT=$((1025 + OFFSET))

# Sanitize directory name for COMPOSE_PROJECT_NAME (alphanumeric + dash only)
# Include OFFSET to ensure unique container names per worktree (even if folder name is the same)
PROJECT_NAME=$(echo "${DIR_NAME}-${OFFSET}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')

# Create .env from example if it doesn't exist
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

# Function to update or add an environment variable
update_env_var() {
    local key=$1
    local value=$2
    if [ -f .env ]; then
        if grep -q "^${key}=" .env; then
            # Variable exists (uncommented), update all occurrences
            sed -i "s|^${key}=.*|${key}=${value}|" .env
        elif grep -q "^# *${key}=" .env; then
            # Variable is commented out, uncomment and update only the first occurrence
            sed -i "0,\|^# *${key}=.*|s|^# *${key}=.*|${key}=${value}|" .env
        else
            # Variable doesn't exist, append to file
            echo "${key}=${value}" >> .env
        fi
    else
        # No .env file, create one with just this variable
        echo "${key}=${value}" >> .env
    fi
}

# Function to generate a random secret (32 chars alphanumeric)
generate_secret() {
    openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32
}

# Function to generate a hex-encoded 32-byte key (64 hex chars, required by pgsodium)
generate_hex_key() {
    head -c 32 /dev/urandom | od -A n -t x1 | tr -d ' \n'
}

# Function to add a variable only if it doesn't exist (for secrets)
generate_if_missing() {
    local key=$1
    local value=$2
    if [ -f .env ]; then
        if ! grep -q "^${key}=" .env; then
            echo "${key}=${value}" >> .env
        fi
    else
        echo "${key}=${value}" >> .env
    fi
}

# =============================================================================
# Supabase JWT credentials (must match - keys are signed with the secret)
# Using official Supabase demo credentials (same as `supabase init`)
# For production (Coolify), these are auto-populated via SERVICE_* variables
# =============================================================================
SUPABASE_JWT_SECRET="super-secret-jwt-token-with-at-least-32-characters-long"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"

# Generate all required SERVICE_* variables (only if they don't exist)
generate_if_missing "SERVICE_PASSWORD_POSTGRES" "$(generate_secret)"
generate_if_missing "SERVICE_PASSWORD_JWT" "$SUPABASE_JWT_SECRET"
generate_if_missing "SERVICE_SUPABASEANON_KEY" "$SUPABASE_ANON_KEY"
generate_if_missing "SERVICE_SUPABASESERVICE_KEY" "$SUPABASE_SERVICE_KEY"
# Generate shared secret for LOGFLARE (needed both as LOGFLARE_API_KEY and SERVICE_PASSWORD_LOGFLARE)
_logflare_secret=$(generate_secret)
generate_if_missing "LOGFLARE_API_KEY" "$_logflare_secret"
generate_if_missing "SERVICE_PASSWORD_LOGFLARE" "$_logflare_secret"
generate_if_missing "SERVICE_PASSWORD_METACRYPTO" "$(generate_secret)"
generate_if_missing "SERVICE_PASSWORD_REALTIME" "$(generate_secret)"
generate_if_missing "SERVICE_PASSWORD_SUPAVISORSECRET" "$(generate_secret)"
generate_if_missing "SERVICE_PASSWORD_VAULTENC" "$(generate_secret)"
generate_if_missing "SERVICE_PASSWORD_PGSODIUM" "$(generate_hex_key)"
generate_if_missing "SERVICE_USER_MINIO" "minioadmin"
generate_if_missing "SERVICE_PASSWORD_MINIO" "$(generate_secret)"
generate_if_missing "SERVICE_USER_ADMIN" "admin"
generate_if_missing "SERVICE_PASSWORD_ADMIN" "$(generate_secret)"

# Update the port variables
update_env_var "COMPOSE_PROJECT_NAME" "$PROJECT_NAME"
update_env_var "NEXTJS_PORT" "$NEXTJS_PORT"
update_env_var "KONG_PORT" "$KONG_PORT"
update_env_var "POSTGRES_PORT" "$POSTGRES_PORT"
update_env_var "POOLER_PORT" "$POOLER_PORT"
update_env_var "MAILPIT_HTTP_PORT" "$MAILPIT_HTTP_PORT"
update_env_var "MAILPIT_SMTP_PORT" "$MAILPIT_SMTP_PORT"

# Set Next.js Supabase environment variables
update_env_var "NEXT_PUBLIC_SUPABASE_ANON_KEY" "$SUPABASE_ANON_KEY"
update_env_var "SUPABASE_SERVICE_KEY" "$SUPABASE_SERVICE_KEY"
update_env_var "NEXT_PUBLIC_SUPABASE_URL" "http://localhost:${KONG_PORT}"
update_env_var "SUPABASE_URL" "http://localhost:${KONG_PORT}"
update_env_var "NEXT_PUBLIC_FRONTEND_URL" "http://localhost:${NEXTJS_PORT}"

# =============================================================================
# Read back generated secrets from .env for display
# =============================================================================
get_env_var() {
    local key=$1
    grep "^${key}=" .env 2>/dev/null | cut -d= -f2-
}

POSTGRES_PASSWORD=$(get_env_var "SERVICE_PASSWORD_POSTGRES")
JWT_SECRET=$(get_env_var "SERVICE_PASSWORD_JWT")
ANON_KEY=$(get_env_var "SERVICE_SUPABASEANON_KEY")
SERVICE_KEY=$(get_env_var "SERVICE_SUPABASESERVICE_KEY")
ADMIN_USER=$(get_env_var "SERVICE_USER_ADMIN")
ADMIN_PASSWORD=$(get_env_var "SERVICE_PASSWORD_ADMIN")

# Truncate keys for display (show first 50 chars + ...)
truncate_key() {
    local key=$1
    if [ ${#key} -gt 50 ]; then
        echo "${key:0:50}..."
    else
        echo "$key"
    fi
}

# Function to display credentials info
print_info() {
    echo "=========================================="
    echo "Worktree configured: $DIR_NAME"
    echo "=========================================="
    echo "Project:    $PROJECT_NAME (offset: $OFFSET)"
    echo ""
    echo "Ports:"
    echo "  Next.js:    http://localhost:${NEXTJS_PORT}"
    echo "  Supabase:   http://localhost:${KONG_PORT}"
    echo "  PostgreSQL: localhost:${POSTGRES_PORT}"
    echo "  Pooler:     localhost:${POOLER_PORT}"
    echo "  Mailpit:    http://localhost:${MAILPIT_HTTP_PORT} (SMTP: ${MAILPIT_SMTP_PORT})"
    echo ""
    echo "Credentials:"
    echo "  JWT Secret:           $JWT_SECRET"
    echo "  Supabase Anon Key:    $(truncate_key "$ANON_KEY")"
    echo "  Supabase Service Key: $(truncate_key "$SERVICE_KEY")"
    echo ""
    echo "Database:"
    echo "  URL: postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres"
    echo ""
    echo "Supabase Studio:"
    echo "  URL:      http://localhost:${KONG_PORT}"
    echo "  Username: $ADMIN_USER"
    echo "  Password: $ADMIN_PASSWORD"
    echo "=========================================="
}

# Function to check if main services are already running
services_running() {
    # Check if the main containers are running (nextjs-app and supabase-db)
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${PROJECT_NAME}-nextjs-app$" && \
       docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${PROJECT_NAME}-supabase-db$"; then
        return 0
    fi
    return 1
}

# Check if services are already running (skip heavy operations unless --force)
if [ "$FORCE" = false ] && services_running; then
    echo ""
    echo "Services are already running. Use --force to restart."
    echo ""
    print_info
    echo ""
    echo "Commands:"
    echo "  View logs: docker compose -f docker-compose.development.yml logs -f"
    echo "  Stop:      docker compose -f docker-compose.development.yml down"
    echo "  Restart:   docker compose -f docker-compose.development.yml down && docker compose -f docker-compose.development.yml up -d"
    echo ""
    echo "Migrations:"
    echo "  Apply:     PGSSLMODE=disable npx supabase db push --db-url 'postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres' --include-all"
    echo ""
    echo "Database:"
    echo "  Reset:     PGSSLMODE=disable npx supabase db reset --db-url 'postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres'"
    echo "=========================================="
    echo ""
    echo "Success! Next.js app available at: http://localhost:${NEXTJS_PORT}"
    if [ "$LIVE" = true ]; then
        echo ""
        echo "Streaming Next.js logs (Ctrl+C to stop)..."
        echo ""
        docker compose -f docker-compose.development.yml logs -f nextjs-app
    else
        exit 0
    fi
fi

# Show info before docker starts (full run path)
print_info

# Note: pnpm store is now persisted in a Docker volume (pnpm-store)
# No need to delete local .pnpm-store - packages are cached between restarts

echo ""
echo "Starting Docker Compose..."
echo ""

# Export HOST_UID and HOST_GID for Docker to run as current user (fixes node_modules permissions)
# Note: We use HOST_UID/HOST_GID instead of UID/GID because UID is a readonly bash builtin
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)

docker compose -f docker-compose.development.yml up -d

# Wait for database to be healthy
echo ""
echo "Waiting for database to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
until docker exec ${PROJECT_NAME}-supabase-db pg_isready -U postgres -h 127.0.0.1 > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "Database did not become ready in time. Skipping migrations."
        break
    fi
    echo "  Waiting for database... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

# Run migrations if database is ready and migrations directory exists
if [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ -d "supabase/migrations" ]; then
    echo ""
    echo "Running Supabase migrations..."
    PGSSLMODE=disable npx supabase db push --db-url "postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres" --include-all --yes || echo "Migration failed or no changes to apply"
fi

# Run seed if seed file exists and database is ready
if [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ -f "supabase/seed.sql" ]; then
    echo ""
    echo "Running database seed..."
    PGSSLMODE=disable psql "postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres" \
        -f supabase/seed.sql \
        && echo "Seed completed successfully." \
        || echo "Seed failed or already applied. Continuing..."
fi

# Wait for Next.js app to be ready
echo ""
echo "Waiting for Next.js app to be ready..."
NEXTJS_RETRIES=0
NEXTJS_MAX_RETRIES=150  # 5 minutes max (150 * 2 seconds)
until curl -s -o /dev/null -w "%{http_code}" "http://localhost:${NEXTJS_PORT}" | grep -qE "^[23]"; do
    NEXTJS_RETRIES=$((NEXTJS_RETRIES + 1))
    if [ $NEXTJS_RETRIES -ge $NEXTJS_MAX_RETRIES ]; then
        echo "  Next.js app did not become ready in time."
        echo "  Check logs: docker compose -f docker-compose.development.yml logs -f nextjs-app"
        break
    fi
    echo "  Waiting for Next.js... ($NEXTJS_RETRIES/$NEXTJS_MAX_RETRIES)"
    sleep 2
done

if [ $NEXTJS_RETRIES -lt $NEXTJS_MAX_RETRIES ]; then
    echo "  Next.js app is ready!"
fi

# Show info again after docker output (easy to see at end)
echo ""
print_info
echo ""
echo "Commands:"
echo "  View logs: docker compose -f docker-compose.development.yml logs -f"
echo "  Stop:      docker compose -f docker-compose.development.yml down"
echo "  Restart:   docker compose -f docker-compose.development.yml down && docker compose -f docker-compose.development.yml up -d"
echo ""
echo "Migrations:"
echo "  Apply:     PGSSLMODE=disable npx supabase db push --db-url 'postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres' --include-all"
echo ""
echo "Database:"
echo "  Reset:     PGSSLMODE=disable npx supabase db reset --db-url 'postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres'"
echo "=========================================="

echo ""
echo "Success! Next.js app available at: http://localhost:${NEXTJS_PORT}"

if [ "$LIVE" = true ]; then
    echo ""
    echo "Streaming Next.js logs (Ctrl+C to stop)..."
    echo ""
    docker compose -f docker-compose.development.yml logs -f nextjs-app
else
    exit 0
fi
