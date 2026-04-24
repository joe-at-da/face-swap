/* eslint-disable react-hooks/rules-of-hooks */
import fs from "fs";
import path from "path";
import { test as base, type Page, type Browser } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";
import {
  createTestSupabaseAdmin,
  type TestSupabaseAdmin,
} from "../helpers/supabase-admin";
import {
  TEST_USERS,
  getProjectWorkerEmail,
  getProjectWorkerKey,
  type TestUser,
  type TestEmail,
} from "../helpers/test-users";
import { MP_ALPHA_ID } from "../helpers/constants";
import { SUPABASE_COOKIE_NAME } from "@/supabase/cookieConfig";


/** Stored user IDs written by global-setup.ts (cached at module scope) */
let _userIds: Record<string, string> | null = null;
function loadUserIds(): Record<string, string> {
  if (_userIds) return _userIds;
  const idsPath = path.join(__dirname, "../../.test-user-ids.json");
  if (!fs.existsSync(idsPath)) {
    throw new Error(
      ".test-user-ids.json not found — did global setup run? " +
        "Expected at: " +
        idsPath
    );
  }
  _userIds = JSON.parse(fs.readFileSync(idsPath, "utf-8")) as Record<string, string>;
  return _userIds!;
}

type TestFixtures = {
  supabaseAdmin: TestSupabaseAdmin;
  testUser: TestUser & { userId: string };
  adminUser: TestUser & { userId: string };
  setupUser: TestUser & { userId: string };
  mpUser: TestUser & { userId: string };
  ldMpUser: TestUser & { userId: string };
  teamMemberUser: TestUser & { userId: string };
  removedTeamMemberUser: TestUser & { userId: string };
  authenticatedPage: Page;
  adminPage: Page;
  ldMpPage: Page;
  setupUserPage: Page;
  mpSetupPage: Page;
  mpAuthenticatedPage: Page;
  teamSetupPage: Page;
  noTeamAccessPage: Page;
};

type WorkerFixtures = {
  workerStorageState: string;
  workerAdminStorageState: string;
  workerMpStorageState: string;
  workerLdMpStorageState: string;
};

type ResolvedTestUser = TestUser & { userId: string };

/**
 * Create a worker-scoped storage state fixture.
 *
 * Each worker project gets its own email
 * (e.g. e2e-regular-user-firefox-w3@test.local) to eliminate both
 * cross-worker generateLink() rate-limit collisions and cross-browser
 * state pollution on the same worker index.
 * Auth files are per-project+worker: `.auth-regular-firefox-w0.json`, etc.
 * Cached for 30 minutes to stay within JWT expiry window.
 */
function createWorkerAuth(label: string, baseName: string, baseEmail: TestEmail) {
  const fixture = async (
    { browser }: { browser: Browser },
    use: (s: string) => Promise<void>,
    workerInfo: import("@playwright/test").WorkerInfo
  ) => {
    const idx = workerInfo.parallelIndex;
    const projectName = workerInfo.project.name;
    const userKey = getProjectWorkerKey(baseName, projectName, idx);
    const normalizedProject = userKey.replace(`${baseName}-`, "").replace(`-w${idx}`, "");
    const email = getProjectWorkerEmail(baseEmail, projectName, idx);
    const authDir = path.resolve(__dirname, "../../.auth-states");
    if (!fs.existsSync(authDir)) fs.mkdirSync(authDir, { recursive: true });
    const fileName = path.resolve(authDir, `.auth-${label}-${normalizedProject}-w${idx}.json`);
    const lockFile = path.resolve(authDir, `.auth-${label}-${normalizedProject}-w${idx}.lock`);

    // If a valid cached file exists, reuse it — but only if the user ID
    // matches the current test user (global teardown+setup recreates users
    // with new IDs between runs)
    if (fs.existsSync(fileName)) {
      const ageMs = Date.now() - fs.statSync(fileName).mtimeMs;
      if (ageMs < 30 * 60 * 1000) {
        let cacheValid = false;
        try {
          const stored = JSON.parse(fs.readFileSync(fileName, "utf-8"));
          const cookie = stored.cookies?.find((c: { name: string }) =>
            c.name.startsWith("sb-")
          );
          if (cookie) {
            const session = JSON.parse(cookie.value);
            const storedUserId = session?.user?.id;
            const ids = loadUserIds();
            if (storedUserId && ids[userKey] === storedUserId) {
              cacheValid = true;
            }
          }
        } catch {
          // Corrupted cache — regenerate
        }
        if (cacheValid) {
          await use(fileName);
          return;
        }
        // Stale user ID — delete cache to force regeneration
        try { fs.unlinkSync(fileName); } catch { /* ignore */ }
      }
    }

    // Clean up stale lockfiles (older than 60s = crashed worker)
    if (fs.existsSync(lockFile)) {
      const lockAge = Date.now() - fs.statSync(lockFile).mtimeMs;
      if (lockAge > 60_000) {
        try { fs.unlinkSync(lockFile); } catch { /* ignore */ }
      }
    }

    // Per-worker emails mean no cross-worker contention, but we still use
    // lockfiles to handle multiple browser projects sharing the same worker index
    let acquired = false;
    try {
      fs.writeFileSync(lockFile, String(process.pid), { flag: "wx" });
      acquired = true;
    } catch {
      // Lock exists — another browser project is generating for this worker
    }

    if (acquired) {
      try {
        const context = await browser.newContext();
        const page = await context.newPage();
        const admin = createTestSupabaseAdmin();
        await injectSession(page, admin, email);
        await page.context().storageState({ path: fileName });
        await context.close();
      } finally {
        try { fs.unlinkSync(lockFile); } catch { /* ignore */ }
      }
    } else {
      // Poll until the generating worker creates the file (up to 30s)
      const deadline = Date.now() + 30_000;
      while (!fs.existsSync(fileName) && Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 500));
      }
      if (!fs.existsSync(fileName)) {
        throw new Error(`Auth state ${fileName} not created within 30s`);
      }
    }

    await use(fileName);
  };
  return [fixture, { scope: "worker" as const }] as [typeof fixture, { scope: "worker" }];
}

function resolveProjectUser(
  baseName: string,
  baseUser: TestUser,
  projectName: string,
  workerIndex: number
): ResolvedTestUser {
  const ids = loadUserIds();
  const projectKey = getProjectWorkerKey(baseName, projectName, workerIndex);
  return {
    ...baseUser,
    email: getProjectWorkerEmail(baseUser.email, projectName, workerIndex),
    userId: ids[projectKey] ?? ids[baseName],
  };
}

export const test = base.extend<TestFixtures, WorkerFixtures>({
  /**
   * Supabase admin client for DB verification in tests.
   */
  // eslint-disable-next-line no-empty-pattern
  supabaseAdmin: async ({}, use) => {
    const admin = createTestSupabaseAdmin();
    await use(admin);
  },

  /**
   * Per-worker regular test user details (matches the per-worker auth fixture email).
   */
  // eslint-disable-next-line no-empty-pattern
  testUser: async ({}, use, testInfo) => {
    const ids = loadUserIds();
    const idx = testInfo.parallelIndex;
    const workerKey = getProjectWorkerKey("regularUser", testInfo.project.name, idx);
    await use({
      ...TEST_USERS.regularUser,
      email: getProjectWorkerEmail(TEST_USERS.regularUser.email, testInfo.project.name, idx),
      userId: ids[workerKey] ?? ids.regularUser,
    });
  },

  /**
   * Per-worker admin test user details.
   */
  // eslint-disable-next-line no-empty-pattern
  adminUser: async ({}, use, testInfo) => {
    const ids = loadUserIds();
    const idx = testInfo.parallelIndex;
    const workerKey = getProjectWorkerKey("adminUser", testInfo.project.name, idx);
    await use({
      ...TEST_USERS.adminUser,
      email: getProjectWorkerEmail(TEST_USERS.adminUser.email, testInfo.project.name, idx),
      userId: ids[workerKey] ?? ids.adminUser,
    });
  },

  // eslint-disable-next-line no-empty-pattern
  setupUser: async ({}, use, testInfo) => {
    await use(
      resolveProjectUser(
        "setupUser",
        TEST_USERS.setupUser,
        testInfo.project.name,
        testInfo.parallelIndex
      )
    );
  },

  // eslint-disable-next-line no-empty-pattern
  mpUser: async ({}, use, testInfo) => {
    await use(
      resolveProjectUser(
        "mpUser",
        TEST_USERS.mpUser,
        testInfo.project.name,
        testInfo.parallelIndex
      )
    );
  },

  // eslint-disable-next-line no-empty-pattern
  ldMpUser: async ({}, use, testInfo) => {
    await use(
      resolveProjectUser(
        "ldMpUser",
        TEST_USERS.ldMpUser,
        testInfo.project.name,
        testInfo.parallelIndex
      )
    );
  },

  // eslint-disable-next-line no-empty-pattern
  teamMemberUser: async ({}, use, testInfo) => {
    await use(
      resolveProjectUser(
        "teamMember",
        TEST_USERS.teamMember,
        testInfo.project.name,
        testInfo.parallelIndex
      )
    );
  },

  // eslint-disable-next-line no-empty-pattern
  removedTeamMemberUser: async ({}, use, testInfo) => {
    await use(
      resolveProjectUser(
        "removedTeamMember",
        TEST_USERS.removedTeamMember,
        testInfo.project.name,
        testInfo.parallelIndex
      )
    );
  },

  // ── Worker-scoped storage states (per-worker emails) ─────────────
  //
  // Each worker project uses its own email (e.g. e2e-regular-user-firefox-w3@test.local).
  // Auth states are isolated per browser project and worker index.

  workerStorageState: createWorkerAuth("regular", "regularUser", TEST_USERS.regularUser.email),
  workerAdminStorageState: createWorkerAuth("admin", "adminUser", TEST_USERS.adminUser.email),
  workerMpStorageState: createWorkerAuth("mp", "mpCompletedUser", TEST_USERS.mpCompletedUser.email),
  workerLdMpStorageState: createWorkerAuth("ld-mp", "ldMpUser", TEST_USERS.ldMpUser.email),

  // ── Test-scoped pages (from worker-scoped auth) ───────────────────

  /**
   * Browser page pre-authenticated as regular user (worker-scoped auth).
   */
  authenticatedPage: async ({ browser, workerStorageState }, use) => {
    const context = await browser.newContext({
      storageState: workerStorageState,
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  /**
   * Browser page pre-authenticated as admin user (worker-scoped auth).
   */
  adminPage: async ({ browser, workerAdminStorageState }, use) => {
    const context = await browser.newContext({
      storageState: workerAdminStorageState,
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  /**
   * Browser page pre-authenticated as LD MP user (worker-scoped auth).
   * Used for LD cross-party clip tests.
   */
  ldMpPage: async ({ browser, workerLdMpStorageState }, use) => {
    const context = await browser.newContext({
      storageState: workerLdMpStorageState,
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  /**
   * Browser page pre-authenticated as MP completed user (worker-scoped auth).
   */
  mpAuthenticatedPage: async ({ browser, workerMpStorageState }, use) => {
    const context = await browser.newContext({
      storageState: workerMpStorageState,
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // ── Test-scoped setup fixtures (project+worker-scoped mutable users) ────
  //
  // These users mutate setup state (is_first_login, member_id, team membership
  // lookups), so each browser project + worker gets its own dedicated identity.

  /**
   * Authenticated as setup user (is_first_login: true). Lands on /setup.
   * Resets user state after test.
   */
  setupUserPage: async ({ browser, supabaseAdmin, setupUser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await injectSession(
      page,
      supabaseAdmin,
      setupUser.email,
      /\/(setup|dashboard)/
    );
    await use(page);
    await context.close();

    // Reset user state for next test
    await supabaseAdmin
      .from("user_roles")
      .update({ is_first_login: true, member_id: null })
      .eq("user_id", setupUser.userId);
    await supabaseAdmin.auth.admin.updateUserById(setupUser.userId, {
      user_metadata: { is_first_login: true, is_parliament_member: false },
    });
  },

  /**
   * Authenticated as MP user (is_first_login: true, @veedoo.io). Lands on /mp-setup.
   * Resets user state after test.
   */
  mpSetupPage: async ({ browser, supabaseAdmin, mpUser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await injectSession(
      page,
      supabaseAdmin,
      mpUser.email,
      /\/(mp-setup|dashboard)/
    );
    await use(page);
    await context.close();

    // Reset user state
    await supabaseAdmin
      .from("user_roles")
      .update({ is_first_login: true, member_id: MP_ALPHA_ID })
      .eq("user_id", mpUser.userId);
    await supabaseAdmin.auth.admin.updateUserById(mpUser.userId, {
      user_metadata: { is_first_login: true, is_parliament_member: true },
    });
  },

  /**
   * Authenticated as team member (is_first_login: true). Lands on /team-setup.
   * Resets user state after test.
   */
  teamSetupPage: async ({ browser, supabaseAdmin, teamMemberUser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await injectSession(
      page,
      supabaseAdmin,
      teamMemberUser.email,
      /\/(team-setup|dashboard)/
    );
    await use(page);
    await context.close();

    // Reset user state
    await supabaseAdmin
      .from("user_roles")
      .update({ is_first_login: true })
      .eq("user_id", teamMemberUser.userId);
    await supabaseAdmin.auth.admin.updateUserById(teamMemberUser.userId, {
      user_metadata: {
        is_first_login: true,
        is_team_member: true,
        is_parliament_member: false,
      },
    });
  },

  /**
   * Authenticated as removed team member. Lands on /no-team-access.
   */
  noTeamAccessPage: async ({ browser, supabaseAdmin, removedTeamMemberUser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await injectSession(
      page,
      supabaseAdmin,
      removedTeamMemberUser.email,
      /\/(no-team-access|dashboard)/
    );
    await use(page);
    await context.close();
  },
});

/**
 * Inject a valid Supabase session into the browser via cookie injection.
 *
 * Approach:
 * 1. admin.generateLink() → get hashed_token
 * 2. supabase.auth.verifyOtp({ token_hash }) → get session tokens
 * 3. Set session as Supabase SSR cookies on the browser context
 * 4. Navigate to /dashboard (or expected route)
 */
export async function injectSession(
  page: Page,
  admin: TestSupabaseAdmin,
  email: string,
  waitForUrlPattern: RegExp = /\/(dashboard|setup|mp-setup|team-setup|no-team-access)/
): Promise<void> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !anonKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY for session injection"
    );
  }

  // Stagger concurrent injectSession calls to reduce GoTrue contention
  await new Promise((r) => setTimeout(r, Math.random() * 1000));

  // Retry loop: concurrent generateLink calls for the same email can invalidate
  // a previous hashed_token before verifyOtp consumes it ("Email link is invalid
  // or has expired"). Retrying with a fresh token resolves the race.
  const MAX_RETRIES = 3;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let session: any = null;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    // Step 1: Generate a magic link to get the hashed_token
    const { data, error } = await admin.auth.admin.generateLink({
      type: "magiclink",
      email,
    });
    if (error) throw new Error(`generateLink failed for ${email}: ${error.message}`);

    const hashedToken = data.properties?.hashed_token;
    if (!hashedToken) throw new Error(`No hashed_token returned for ${email}`);

    // Step 2: Verify the token immediately (fresh client per call)
    const verifyClient = createClient(supabaseUrl, anonKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const result = await verifyClient.auth.verifyOtp({
      token_hash: hashedToken,
      type: "magiclink",
    });

    if (!result.error && result.data.session) {
      session = result.data.session;
      break;
    }

    if (attempt === MAX_RETRIES) {
      throw new Error(
        `verifyOtp failed for ${email} after ${MAX_RETRIES} attempts: ${result.error?.message ?? "no session returned"}`
      );
    }

    // Brief backoff before retrying — let the concurrent call finish
    await new Promise((r) => setTimeout(r, 500 + Math.random() * 500));
  }

  if (!session) throw new Error(`No session returned from verifyOtp for ${email}`);

  // Step 3: Inject session as Supabase SSR cookies
  const COOKIE_NAME = SUPABASE_COOKIE_NAME;
  const BASE_URL =
    process.env.NEXT_PUBLIC_FRONTEND_URL ||
    "http://localhost:3001";
  const sessionJson = JSON.stringify({
    access_token: session.access_token,
    refresh_token: session.refresh_token,
    expires_at: session.expires_at,
    expires_in: session.expires_in,
    token_type: session.token_type,
    user: session.user,
  });

  // Supabase SSR chunks cookies at ~3180 chars
  const CHUNK_SIZE = 3180;
  const chunks: string[] = [];
  for (let i = 0; i < sessionJson.length; i += CHUNK_SIZE) {
    chunks.push(sessionJson.slice(i, i + CHUNK_SIZE));
  }

  const cookies = chunks.map((chunk, i) => ({
    name: chunks.length === 1 ? COOKIE_NAME : `${COOKIE_NAME}.${i}`,
    value: chunk,
    url: BASE_URL,
    httpOnly: false,
    secure: false,
    sameSite: "Lax" as const,
  }));

  await page.context().addCookies(cookies);

  // Step 4: Navigate to dashboard — middleware reads session from cookies
  await page.goto("/dashboard");
  await page.waitForURL(waitForUrlPattern, {
    timeout: 30_000,
  });
}

export { expect } from "@playwright/test";
