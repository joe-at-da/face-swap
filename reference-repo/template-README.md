# Next.js + Supabase Local Development Template

A complete local development stack that runs Next.js alongside a full Supabase instance with hot-reload, automatic database migrations, and multi-worktree support.

## Features

- **Hot-Reload Development** - Code changes reflect instantly without container rebuilds
- **Automatic Migrations** - Database migrations run automatically on container start
- **Package Manager Auto-Detection** - Supports pnpm (preferred) and npm
- **Multi-Worktree Support** - Run up to 50 simultaneous development instances with isolated ports
- **E2E Testing** - Playwright tests with CI/CD integration and automatic report publishing
- **Production Ready** - Includes production Docker Compose for deployment

## Quick Start

```bash
# 1. Copy template files to your Next.js project
cp -r nextjs-supabase-template/* your-nextjs-project/

# 2. Configure environment
cd your-nextjs-project
./setup-worktree.sh

# 3. Start development stack
docker compose -f docker-compose.development.yml up
```

Your app is now running at http://localhost:3001

## Prerequisites

- Docker and Docker Compose
- Node.js 22+ (for local development outside Docker)
- Git (for worktree support)

## Setting Up a New Project

### 1. Copy Template Files

Copy all files from this template to your existing Next.js project:

```bash
cp docker-compose.development.yml your-project/
cp docker-compose.production.yml your-project/
cp Dockerfile your-project/
cp docker-entrypoint.sh your-project/
cp setup-worktree.sh your-project/
cp cleanup-worktree.sh your-project/
cp .env.example your-project/
cp next.config.example.js your-project/  # Reference for standalone output
cp playwright.config.ts your-project/    # E2E test configuration
cp -r tests/ your-project/               # E2E test files
cp -r .github/ your-project/             # CI/CD workflows
```

### 2. Configure next.config.js

Ensure your `next.config.js` has standalone output enabled:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
};

module.exports = nextConfig;
```

### 3. Configure Environment

Run the setup script to configure ports:

```bash
cd your-project
./setup-worktree.sh
```

This creates a `.env` file with automatically assigned ports based on your directory name.

### 4. Start Development

```bash
docker compose -f docker-compose.development.yml up
```

## Development Workflow

### Starting the Stack

```bash
# Start all services
docker compose -f docker-compose.development.yml up

# Start in detached mode
docker compose -f docker-compose.development.yml up -d

# View logs
docker compose -f docker-compose.development.yml logs -f nextjs-app
```

### Stopping the Stack

```bash
# Stop all services
docker compose -f docker-compose.development.yml down

# Stop and remove volumes (resets database)
docker compose -f docker-compose.development.yml down -v
```

### Cleaning Up a Worktree

Use the cleanup script for complete removal of Docker resources:

```bash
# Interactive cleanup (asks for confirmation)
./cleanup-worktree.sh

# Force cleanup without confirmation
./cleanup-worktree.sh --force

# Stop containers but keep database volumes
./cleanup-worktree.sh --keep-volumes

# Full cleanup including .env file
./cleanup-worktree.sh --clean-env
```

### Available URLs

| Service | URL | Description |
|---------|-----|-------------|
| Next.js App | http://localhost:3001 | Your application |
| Supabase Studio | http://localhost:8000 | Database management UI |
| Supabase API | http://localhost:8000 | REST and Realtime API |
| PostgreSQL | localhost:5432 | Direct database connection |
| Connection Pooler | localhost:6543 | Pooled database connection |

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| Supabase Studio | `admin` | `admin` |
| PostgreSQL | `postgres` | Auto-generated (check logs) |

### Hot-Reload Behavior

- **Code Changes**: Instantly reflected in the browser
- **Package Changes**: Container auto-reinstalls dependencies when `package.json` changes
- **Environment Changes**: Requires container restart

### Node Modules Sync (Linux Only)

By default, this template uses **true bidirectional node_modules sync** between your host machine and the container. This means:

- Install packages on your host (`pnpm add lodash`) → immediately available in the container
- Install packages in the container → immediately available on your host
- Your IDE gets full IntelliSense and type definitions

**Why this works on Linux:** Both the host (Linux) and container (Alpine Linux) use the same binary format, so native modules compiled on one work on the other.

### macOS and Windows Compatibility

On macOS and Windows, native Node modules (like `esbuild`, `sharp`, etc.) are compiled for different platforms than the Linux container. To avoid binary incompatibility issues, you need to isolate the container's `node_modules`.

**Add this volume to `docker-compose.development.yml`:**

```yaml
# In the nextjs-app service, modify the volumes section:
volumes:
  - ./:/app                 # Mount local code for hot-reload
  - /app/node_modules       # ADD THIS LINE - Isolate container's node_modules
  - /app/.next              # Exclude build directory
```

**Trade-offs with isolated node_modules:**

| Feature | Linux (synced) | macOS/Windows (isolated) |
|---------|----------------|--------------------------|
| IDE IntelliSense | ✅ Full support | ⚠️ Requires local `npm install` |
| Package install location | Either host or container | Container only |
| Native module compatibility | ✅ Works | ✅ Works |
| Disk space | Shared | Duplicated |

**Recommended workflow for macOS/Windows:**

1. Add the `/app/node_modules` volume isolation line
2. Run `pnpm install` (or `npm install`) locally for IDE support
3. Let the container manage its own `node_modules` for runtime

### Package Manager Support

The template auto-detects your package manager:

| Lock File | Package Manager |
|-----------|-----------------|
| `pnpm-lock.yaml` | pnpm (preferred) |
| `package-lock.json` | npm |

## Database Migrations

### Automatic Migrations

Migrations run automatically when the container starts:

1. Container checks for `supabase/migrations` directory
2. Runs `supabase db push --include-all` to apply all migrations
3. Runs `supabase db seed` if `supabase/seed.sql` exists
4. Starts the Next.js development server

### Creating Migrations

Create migrations in the `supabase/migrations` directory:

```bash
mkdir -p supabase/migrations
```

Name migrations with timestamps for ordering:

```
supabase/migrations/
  20240101000000_create_users.sql
  20240102000000_add_profiles.sql
```

### Manual Migration Commands

Run inside the Next.js container:

```bash
# Apply all migrations
docker compose -f docker-compose.development.yml exec nextjs-app \
  npx supabase db push --db-url "$DIRECT_URL" --include-all

# Seed database
docker compose -f docker-compose.development.yml exec nextjs-app \
  npx supabase db seed --db-url "$DIRECT_URL"
```

### Seeding Data

Create a seed file at `supabase/seed.sql`:

```sql
-- supabase/seed.sql
INSERT INTO public.users (email, name) VALUES
  ('test@example.com', 'Test User');
```

## Multi-Worktree Support

Work on multiple branches simultaneously with isolated environments.

### How It Works

The `setup-worktree.sh` script:

1. Hashes your directory name to generate a unique offset (0-49)
2. Assigns unique ports based on this offset
3. Same directory always gets the same ports (deterministic)

### Using with Git Worktrees

```bash
# Create a new worktree
git worktree add ../my-feature feature-branch

# Configure the new worktree
cd ../my-feature
./setup-worktree.sh

# Start the new instance
docker compose -f docker-compose.development.yml up
```

### Port Assignments

Each worktree gets a unique set of ports:

| Port Type | Base | Range |
|-----------|------|-------|
| Next.js | 3001 | 3001-3050 |
| Supabase API | 8000 | 8000-8049 |
| PostgreSQL | 5432 | 5432-5481 |
| Pooler | 6543 | 6543-6592 |

### Example: Two Worktrees

```
main/          → Next.js: 3005, Supabase: 8005
feature-auth/  → Next.js: 3023, Supabase: 8023
```

### Cleaning Up Worktrees

When a worktree branch is merged and no longer needed, use the cleanup script to remove all Docker resources:

```bash
cd ../my-feature
./cleanup-worktree.sh
```

**Command-line Options:**

| Option | Description |
|--------|-------------|
| `-f, --force` | Skip confirmation prompt |
| `--keep-volumes` | Stop containers but preserve database data |
| `--clean-env` | Also remove the .env file |
| `-h, --help` | Show help message |

The script will:
1. Stop and remove all 15 containers for this worktree
2. Remove associated Docker volumes (database + storage data)
3. Show a summary of cleaned resources

## Production Deployment

### Using docker-compose.production.yml

The production compose file runs only the Next.js application and connects to an external Supabase instance.

```bash
docker compose -f docker-compose.production.yml up -d
```

### Coolify Integration

1. Deploy the parent Supabase stack first (from root `docker-compose.yml`)
2. Deploy this Next.js application second
3. Coolify auto-populates `SERVICE_*` environment variables
4. Ensure `DOCKER_NETWORK` matches the Supabase network (default: `supabase_default`)

### Production Environment Variables

| Variable | Description |
|----------|-------------|
| `SERVICE_URL_SUPABASEKONG` | Public Supabase API URL |
| `SERVICE_SUPABASEANON_KEY` | Anonymous key for client |
| `SERVICE_SUPABASESERVICE_KEY` | Service role key (server-only) |
| `SERVICE_PASSWORD_POSTGRES` | Database password |
| `DOCKER_NETWORK` | Docker network name (default: `supabase_default`) |

## E2E Testing with Playwright

This template includes a complete end-to-end testing setup using Playwright with automated CI/CD integration.

### File Structure

```
tests/
  e2e/                    # E2E test files
    example.spec.ts       # Example test file
playwright.config.ts      # Playwright configuration
.github/workflows/
  e2e-tests.yml           # CI workflow for PR preview testing
```

### Configuration

The `playwright.config.ts` supports multiple environments:

| Priority | Environment Variable | Use Case |
|----------|---------------------|----------|
| 1 | `PLAYWRIGHT_BASE_URL` | CI/CD with Coolify preview URLs |
| 2 | `NEXT_PUBLIC_FRONTEND_URL` | Local development from .env |
| 3 | `http://localhost:3000` | Fallback default |

When `PLAYWRIGHT_BASE_URL` is set, Playwright skips starting a local dev server (assumes external server is running).

### Package.json Setup

Add the following scripts to your `package.json`:

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:report": "playwright show-report"
  }
}
```

| Script | Description |
|--------|-------------|
| `test:e2e` | Run all E2E tests in headless mode |
| `test:e2e:ui` | Run tests with Playwright's interactive UI mode |
| `test:e2e:headed` | Run tests in headed browser (visible) |
| `test:e2e:debug` | Run tests in debug mode with inspector |
| `test:e2e:report` | Open the HTML test report |

### Running Tests Locally

```bash
# Install Playwright browsers (first time only)
pnpm exec playwright install --with-deps chromium

# Run tests against local Docker environment
pnpm test:e2e

# Run tests with UI mode for debugging
pnpm exec playwright test --ui

# Run a specific test file
pnpm exec playwright test tests/e2e/example.spec.ts

# View the HTML report
pnpm exec playwright show-report
```

### Writing Tests

Create test files in `tests/e2e/`:

```typescript
// tests/e2e/homepage.spec.ts
import { test, expect } from '@playwright/test';

test('homepage loads correctly', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/My App/);
});

test('navigation works', async ({ page }) => {
  await page.goto('/');
  await page.click('text=About');
  await expect(page).toHaveURL('/about');
});
```

### CI/CD Workflow

The included GitHub Actions workflow (`.github/workflows/e2e-tests.yml`) automatically:

1. **Triggers** on pull requests (opened, synchronized, reopened)
2. **Waits** for Coolify to deploy a preview environment
3. **Runs** Playwright tests against the preview URL
4. **Publishes** HTML reports to GitHub Pages
5. **Comments** on the PR with a link to the report

### GitHub Pages Setup (Required for Reports)

To enable automatic report publishing, you need to create the `gh-pages` branch and configure GitHub Pages:

**Step 1: Create the gh-pages branch**

```bash
# Create an orphan branch (no commit history)
git checkout --orphan gh-pages

# Reset and create initial content
git reset --hard
echo "# Playwright Reports" > index.html
git add index.html
git commit -m "Initialize gh-pages branch for Playwright reports"

# Push to remote
git push origin gh-pages

# Return to your working branch
git checkout main
```

**Step 2: Configure GitHub Pages**

1. Go to **Settings > Pages** in your GitHub repository
2. Set **Source** to "Deploy from a branch"
3. Set **Branch** to `gh-pages` and folder to `/ (root)`
4. Click **Save**

Reports will be available at: `https://<owner>.github.io/<repo>/reports/pr-<number>/<run-id>/`

### CI Environment Variables

Add these secrets in **Settings > Secrets and variables > Actions**:

| Secret | Description |
|--------|-------------|
| `E2E_TEST_USER_EMAIL` | Test user email for authenticated tests |
| `E2E_TEST_USER_PASSWORD` | Test user password for authenticated tests |

### Test Reports

Each PR gets an automatically generated comment with links to test reports:

- **HTML Report**: Interactive report with screenshots, videos, and traces
- **Artifacts**: Raw test results stored for 30 days
- **History**: Previous run reports remain accessible at their unique URLs

### Playwright Configuration Options

Key settings in `playwright.config.ts`:

| Option | Value | Description |
|--------|-------|-------------|
| `testDir` | `./tests/e2e` | Test file location |
| `fullyParallel` | `true` | Run tests in parallel |
| `retries` | `2` (CI only) | Retry failed tests |
| `workers` | `1` (CI) | Single worker in CI for stability |
| `trace` | `on-first-retry` | Capture traces on retry |
| `screenshot` | `only-on-failure` | Screenshot failed tests |
| `video` | `retain-on-failure` | Record video of failures |

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPOSE_PROJECT_NAME` | Auto-generated | Docker Compose project name |
| `NEXTJS_PORT` | `3001` | Next.js external port |
| `KONG_PORT` | `8000` | Supabase API external port |
| `POSTGRES_PORT` | `5432` | PostgreSQL external port |
| `POOLER_PORT` | `6543` | Connection pooler external port |
| `POSTGRES_DB` | `postgres` | Database name |
| `POOLER_TENANT_ID` | `dev_tenant` | Supavisor tenant identifier |

### Docker Compose Services

| Service | Image | Description |
|---------|-------|-------------|
| `nextjs-app` | `node:22-alpine` | Next.js development server |
| `supabase-kong` | `kong:2.8.1` | API Gateway |
| `supabase-studio` | `supabase/studio` | Database management UI |
| `supabase-db` | `supabase/postgres` | PostgreSQL database |
| `supabase-auth` | `supabase/gotrue` | Authentication service |
| `supabase-rest` | `postgrest/postgrest` | REST API |
| `realtime-dev` | `supabase/realtime` | WebSocket subscriptions |
| `supabase-storage` | `supabase/storage-api` | File storage |
| `supabase-supavisor` | `supabase/supavisor` | Connection pooler |

## Troubleshooting

### Container won't start

**Check Docker is running:**
```bash
docker info
```

**Check for port conflicts:**
```bash
# See what's using the ports
lsof -i :3001
lsof -i :8000
```

**Solution:** Run `./setup-worktree.sh` to get unique ports.

### Migrations fail

**Check the DIRECT_URL is correct:**
```bash
docker compose -f docker-compose.development.yml exec nextjs-app env | grep DIRECT_URL
```

**Check database is healthy:**
```bash
docker compose -f docker-compose.development.yml ps supabase-db
```

### Hot-reload not working

**Ensure volumes are mounted correctly:**
```bash
docker compose -f docker-compose.development.yml exec nextjs-app ls -la /app
```

**Check WATCHPACK_POLLING is enabled:**
```bash
docker compose -f docker-compose.development.yml exec nextjs-app env | grep WATCHPACK
```

### Supabase Studio login fails

**Default credentials:**
- Username: `admin`
- Password: `admin`

**Check Kong is healthy:**
```bash
docker compose -f docker-compose.development.yml ps supabase-kong
```

### Database connection issues

**Check Supavisor is running:**
```bash
docker compose -f docker-compose.development.yml ps supabase-supavisor
```

**Test direct connection:**
```bash
docker compose -f docker-compose.development.yml exec supabase-db \
  pg_isready -U postgres
```

### Reset everything

**Option 1: Using the cleanup script (recommended)**

```bash
# Complete cleanup including .env file
./cleanup-worktree.sh --clean-env

# Start fresh
./setup-worktree.sh
docker compose -f docker-compose.development.yml up
```

**Option 2: Manual reset**

```bash
# Stop containers and remove volumes
docker compose -f docker-compose.development.yml down -v

# Remove generated files
rm -rf node_modules .next

# Start fresh
./setup-worktree.sh
docker compose -f docker-compose.development.yml up
```

## License

MIT
