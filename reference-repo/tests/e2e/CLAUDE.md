# E2E Test Guidelines

## Architecture

```
tests/
  e2e/
    fixtures/           # Playwright custom fixtures (auth, admin client)
    pages/              # Page Object Models (one per page)
    helpers/            # Shared utilities (Supabase, Mailpit, cleanup)
    auth/               # Auth test specs
    <page-name>/        # Future: one folder per page
    CLAUDE.md           # This file
  global-setup.ts       # Pre-seeds test users before all tests
  global-teardown.ts    # Cleans up all test users after all tests
```

## Prerequisites

Tests run against the **Docker Compose dev environment** started by `setup-worktree.sh`. Ensure Docker services are running before executing tests:

```bash
./setup-worktree.sh          # Start all services (idempotent)
./setup-worktree.sh --force  # Force restart
```

All ports, Supabase URLs, keys, and Mailpit URL are read from `.env` (set by `setup-worktree.sh`). There is no separate `.env.e2e` — everything comes from the Docker environment.

## Authentication in Tests

### Pre-authenticated pages (fast — no email involved)

Use the `authenticatedPage` or `adminPage` fixtures for tests that need a logged-in user but aren't testing the login flow itself:

```ts
import { test, expect } from "../fixtures/test-fixtures";

test("dashboard loads for authenticated user", async ({ authenticatedPage }) => {
  await authenticatedPage.goto("/dashboard");
  await expect(authenticatedPage.getByRole("heading")).toBeVisible();
});

test("admin can access admin panel", async ({ adminPage }) => {
  await adminPage.goto("/dashboard/admin");
  // ...
});
```

These fixtures use `admin.auth.admin.generateLink()` + `verifyOtp()` to get session tokens, then inject them as Supabase SSR cookies. No email delivery or browser navigation through GoTrue is involved.

### Full auth flow tests (with email via Mailpit)

For testing actual sign-in/sign-up flows, use the Mailpit helper to retrieve OTP codes or magic links from locally captured emails:

```ts
import { getLatestEmail, extractOtpFromEmail, clearMailbox } from "../helpers/mailpit";

// Always clear the mailbox before sending a new email
await clearMailbox(email);

// Trigger the email (e.g., submit sign-in form)
await signInPage.fillAndSubmitEmail(email);

// Fetch the email from Mailpit (polls with retries)
const message = await getLatestEmail(email);
const otp = extractOtpFromEmail(message!);
```

**Important**: The Docker Compose stack includes a **Mailpit** service. GoTrue sends all emails to Mailpit via SMTP. The Mailpit API URL is derived from `MAILPIT_HTTP_PORT` in `.env` (set by `setup-worktree.sh`).

### Creating test users with Supabase Admin API

Use the `supabaseAdmin` fixture to interact with the database:

```ts
test("verify user in DB", async ({ supabaseAdmin }) => {
  const { data } = await supabaseAdmin
    .from("user_roles")
    .select("role, email")
    .eq("email", testEmail)
    .single();
  expect(data!.role).toBe("user");
});
```

For creating users programmatically:

```ts
import { createTestUser } from "../helpers/test-users";
import { cleanupTestUser } from "../helpers/cleanup";
import { createTestSupabaseAdmin } from "../helpers/supabase-admin";

const admin = createTestSupabaseAdmin();
const userId = await createTestUser(admin, {
  email: "e2e-mytest@test.local",
  role: "user",
  isFirstLogin: false,
});
```

## Rate Limit Avoidance

The Docker GoTrue instance has these rate limits (configured via env vars in `docker-compose.development.yml`):

| Limit | Value | Scope |
|-------|-------|-------|
| `GOTRUE_RATE_LIMIT_EMAIL_SENT` | 100/hour | Per email address |
| `max_frequency` | 1s | Between emails to same address |

**How we stay under limits:**

1. **Pre-seeded users** — `global-setup.ts` creates test users once before all tests run, avoiding repeated sign-up API calls
2. **`email_sent = 100`** — Increased from default of 2
3. **Fixtures bypass email** — `authenticatedPage`/`adminPage` use `generateLink()` instead of sending emails
4. **Clear mailboxes before tests** — Prevents stale emails from interfering

If you add many new email-sending tests, watch for rate limit errors and add small delays between them if needed (`await page.waitForTimeout(1500)`).

5. **Serial mode for shared-email specs** — Test files that send emails to the same address use `test.describe.configure({ mode: "serial" })` to prevent concurrent OTP requests from hitting the `max_frequency` rate limit

### Running E2E tests locally

Ensure the Docker dev environment is running (`./setup-worktree.sh`). Then:

```bash
pnpm test:e2e                           # All browsers
pnpm test:e2e -- --project=chromium     # Chrome only
pnpm test:e2e:headless                  # No HTML report server (for automation)
```

No separate dev server is needed — Playwright connects to the Docker Next.js container.

## Test Data Cleanup

### Naming convention

ALL test emails MUST use the `e2e-` prefix with one of these domains:
- `@test.local` — for regular and admin test users
- `@veedoo.io` — for MP sign-up tests (treated as parliament member)

The cleanup helper **refuses to delete emails** that don't match this pattern. This prevents accidental deletion of real users.

### Cleanup pattern

```ts
test.afterEach(async () => {
  const admin = createTestSupabaseAdmin();
  await cleanupTestUser(admin, "e2e-mytest@test.local");
});
```

- `global-teardown.ts` does a final sweep of ALL `e2e-*` users after the full test suite
- Individual tests that create users should also clean up in `afterEach` for isolation

## DB Verification Pattern

Every test that modifies state should verify both UI and database:

```ts
test("action updates DB correctly", async ({ page, supabaseAdmin }) => {
  // 1. Perform UI action
  await page.getByRole("button", { name: "Submit" }).click();

  // 2. Assert UI shows correct state
  await expect(page.getByText("Success")).toBeVisible();

  // 3. Query Supabase to verify DB state
  const { data } = await supabaseAdmin
    .from("some_table")
    .select("*")
    .eq("id", expectedId)
    .single();
  expect(data).not.toBeNull();
  expect(data!.status).toBe("active");

  // 4. Clean up in afterEach (see above)
});
```

## Test Organization

### File structure

- **One spec file per page**: `auth/sign-in.spec.ts`, `auth/sign-up.spec.ts`, `dashboard/overview.spec.ts`
- **One page object per page**: `pages/sign-in.page.ts`, `pages/sign-up.page.ts`
- **Helpers are shared**: Put reusable utilities in `helpers/`

### Three test categories per feature

Every spec file should have three `test.describe` blocks:

1. **Expected Pass** — Happy path tests that should succeed
2. **Expected Fail** — Tests with invalid input or unauthorized access
3. **Edge Cases** — Race conditions, duplicate submissions, state transitions

```ts
test.describe("Feature — Expected Pass", () => { /* ... */ });
test.describe("Feature — Expected Fail", () => { /* ... */ });
test.describe("Feature — Edge Cases", () => { /* ... */ });
```

### Test per user role

When a feature behaves differently per role, write separate tests:

```ts
test("regular user sees limited dashboard", async ({ authenticatedPage }) => { /* ... */ });
test("admin user sees full dashboard", async ({ adminPage }) => { /* ... */ });
```

## Browser Coverage

Tests run on 5 browser configurations:
- `chromium` — Desktop Chrome
- `firefox` — Desktop Firefox
- `webkit` — Desktop Safari
- `mobile-chrome` — Pixel 5 (mobile Chrome)
- `mobile-safari` — iPhone 13 (mobile Safari)

Run specific browsers:
```bash
pnpm test:e2e:auth                      # Chrome only, auth tests
pnpm test:e2e:mobile -- tests/e2e/auth/ # Mobile browsers only
pnpm test:e2e -- --project=firefox      # Firefox only
```

## Writing New Tests Checklist

- [ ] Use `e2e-` prefix for all test emails
- [ ] Clean up created users in `afterEach`
- [ ] Clear mailbox before sending emails
- [ ] Verify both UI state AND database state
- [ ] Include tests for pass, fail, and edge cases
- [ ] Use Page Object Model for UI interactions
- [ ] Use fixtures for auth (`authenticatedPage`, `adminPage`)
- [ ] Use `supabaseAdmin` fixture for DB queries

## Discovering UI Selectors with Playwright MCP

Before writing a test for any page, **load the page in Playwright MCP browser first** to inspect the rendered HTML and discover the correct selectors:

1. Navigate to the page: `mcp__playwright__browser_navigate` → `http://localhost:<NEXTJS_PORT>/<page-path>` (check `.env` for your port)
2. Take a snapshot: `mcp__playwright__browser_snapshot` — returns the full accessible DOM tree with roles, names, and data attributes
3. Identify elements to target: look for `role`, `name`, `data-slot`, `data-*` attributes, and visible text
4. Build Page Object Model locators from what you see — never guess selectors

**Why this matters:**
- Pages may render differently than expected (conditional elements, dynamic content, Radix UI slots)
- Shadcn/ui components add attributes like `data-slot="alert"` that aren't obvious from source code alone
- Snapshot output shows the exact accessible tree Playwright will interact with

```ts
// Example: discovering that the error alert uses data-slot
// Snapshot reveals: <div data-slot="alert" class="text-destructive">...</div>
// So the correct locator is:
this.errorAlert = page.locator("[data-slot='alert'].text-destructive");
```

## Writing Mobile Tests

When writing or debugging tests for mobile browsers (`mobile-chrome`, `mobile-safari`), use Playwright MCP at mobile resolution to discover mobile-specific UI differences:

1. Resize the browser to mobile viewport before inspecting:
   - Pixel 5: `mcp__playwright__browser_resize` → width: 393, height: 851
   - iPhone 13: `mcp__playwright__browser_resize` → width: 390, height: 844
2. Take a snapshot at mobile resolution — mobile layouts often differ from desktop:
   - Navigation may collapse into a hamburger menu
   - Layouts switch from horizontal to stacked
   - Some elements may be hidden or replaced at small viewports
3. Verify selectors at mobile resolution — a selector that works on desktop may not exist or may match different elements on mobile
4. Use `mcp__playwright__browser_take_screenshot` to visually verify the mobile layout

**Test project names** (from `playwright.config.ts`):
- `mobile-chrome` — Pixel 5 emulation
- `mobile-safari` — iPhone 13 emulation

Run mobile tests only:
```bash
pnpm test:e2e:mobile -- tests/e2e/auth/
```

## Browsing Protected Pages with Playwright MCP

When using Playwright MCP (`mcp__playwright__browser_*`) to inspect a page that requires authentication, you need to inject a valid Supabase session into the browser. Here's the approach:

### Prerequisites

The Docker dev environment must be running (`./setup-worktree.sh`). The dev server uses the same Supabase instance that tests generate tokens against.

### Injecting a Session via Playwright MCP

The session injection approach is implemented in `injectSession()` in `tests/e2e/fixtures/test-fixtures.ts`. The key steps are:

1. `admin.auth.admin.generateLink({ type: "magiclink", email })` → get `hashed_token`
2. `verifyOtp({ token_hash: hashedToken, type: "magiclink" })` → get session tokens
3. Chunk the session JSON at ~3180 chars and inject as Supabase SSR cookies
4. Navigate to `/dashboard` — middleware reads session from cookies

For Playwright MCP (manual browser inspection), use `mcp__playwright__browser_run_code` with the same approach but calling the Supabase REST API directly via `fetch()` from the browser context. The raw REST API returns `hashed_token` at the top level (not inside `data.properties` like the JS client).

### Key details

- **Cookie name**: `sb-mpai-auth-token` (from `supabase/cookieConfig.ts`)
- **REST API difference**: The raw Supabase REST API returns `hashed_token` at the top level of the response, not inside `data.properties` like the JS client
- **Test users**: `e2e-regular-user@test.local` (role: user), `e2e-admin-user@test.local` (role: admin) — pre-seeded by `global-setup.ts`
- **Credentials**: Read `SUPABASE_SERVICE_KEY` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from `.env`

### If this approach doesn't work

If session injection fails (e.g., Supabase version changes, cookie format changes):
1. Try signing in through the UI manually — navigate to `/signin`, enter a test user email, retrieve the OTP from Mailpit (check `.env` for `MAILPIT_HTTP_PORT`), and enter it
2. If neither approach works, ask the user for help authenticating
