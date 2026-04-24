import type { TestSupabaseAdmin } from "./supabase-admin";

/**
 * Template literal type enforcing the e2e-* prefix convention.
 */
type TestEmailPrefix = `e2e-${string}`;
type TestEmailDomain = "test.local" | "veedoo.io";
export type TestEmail = `${TestEmailPrefix}@${TestEmailDomain}`;

/** Max parallel workers — per-worker user variants are created for 0..MAX_WORKERS-1 */
export const MAX_WORKERS = 12;

export const PLAYWRIGHT_PROJECTS = [
  "chromium",
  "firefox",
  "webkit",
  "mobile-chrome",
  "mobile-safari",
] as const;

export type PlaywrightProjectName = (typeof PLAYWRIGHT_PROJECTS)[number];

function normalizeProjectName(projectName: string): string {
  return projectName.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

/**
 * Derive a per-worker email from a base test email.
 * e.g. getWorkerEmail("e2e-regular-user@test.local", 3) → "e2e-regular-user-w3@test.local"
 */
export function getWorkerEmail(baseEmail: TestEmail, workerIndex: number): TestEmail {
  const [local, domain] = baseEmail.split("@");
  return `${local}-w${workerIndex}@${domain}` as TestEmail;
}

/**
 * Derive a per-project+worker email to isolate browser projects from each other.
 * e.g. getProjectWorkerEmail("e2e-regular-user@test.local", "mobile-safari", 3)
 *   → "e2e-regular-user-mobile-safari-w3@test.local"
 */
export function getProjectWorkerEmail(
  baseEmail: TestEmail,
  projectName: string,
  workerIndex: number
): TestEmail {
  const [local, domain] = baseEmail.split("@");
  const normalizedProject = normalizeProjectName(projectName);
  return `${local}-${normalizedProject}-w${workerIndex}@${domain}` as TestEmail;
}

export function getProjectWorkerKey(
  baseName: string,
  projectName: string,
  workerIndex: number
): string {
  return `${baseName}-${normalizeProjectName(projectName)}-w${workerIndex}`;
}

/**
 * Derive a per-project email from a base test email.
 * e.g. getProjectEmail("e2e-setup-user@test.local", "firefox")
 *   → "e2e-setup-user-firefox@test.local"
 */
export function getProjectEmail(
  baseEmail: TestEmail,
  projectName: string
): TestEmail {
  const [local, domain] = baseEmail.split("@");
  const normalizedProject = normalizeProjectName(projectName);
  return `${local}-${normalizedProject}@${domain}` as TestEmail;
}

export function getProjectKey(baseName: string, projectName: string): string {
  return `${baseName}-${normalizeProjectName(projectName)}`;
}

export interface TestUser {
  email: TestEmail;
  role: "admin" | "user";
  userId?: string;
  isFirstLogin?: boolean;
  isParliamentMember?: boolean;
  /** Extra auth.users user_metadata fields */
  userMetadata?: Record<string, unknown>;
}

/**
 * Pre-defined test users created in global setup.
 * All emails use the "e2e-" prefix for safe cleanup.
 */
export const TEST_USERS = {
  regularUser: {
    email: "e2e-regular-user@test.local" as TestEmail,
    role: "user" as const,
  },
  adminUser: {
    email: "e2e-admin-user@test.local" as TestEmail,
    role: "admin" as const,
  },
  setupUser: {
    email: "e2e-setup-user@test.local" as TestEmail,
    role: "user" as const,
    isFirstLogin: true,
  },
  mpUser: {
    email: "e2e-mp-user@veedoo.io" as TestEmail,
    role: "user" as const,
    isFirstLogin: true,
    isParliamentMember: true,
  },
  mpCompletedUser: {
    email: "e2e-mp-completed@veedoo.io" as TestEmail,
    role: "user" as const,
    isFirstLogin: false,
    isParliamentMember: true,
  },
  teamMember: {
    email: "e2e-team-member@test.local" as TestEmail,
    role: "user" as const,
    isFirstLogin: true,
    userMetadata: { is_team_member: true },
  },
  removedTeamMember: {
    email: "e2e-removed-team@test.local" as TestEmail,
    role: "user" as const,
    isFirstLogin: false,
    userMetadata: { is_team_member: true },
  },
  /** LD MP user (member_id → MP_GAMMA_ID with party_id=17). Used for LD cross-party clip tests. */
  ldMpUser: {
    email: "e2e-ld-mp@test.local" as TestEmail,
    role: "user" as const,
    isFirstLogin: false,
  },
  /** Dedicated user for sign-in form tests (OTP/magic-link). Avoids rate-limit collisions with auth fixtures. */
  signinUser: {
    email: "e2e-signin-user@test.local" as TestEmail,
    role: "user" as const,
    isFirstLogin: false,
  },
} as const;

/** Ad-hoc test emails used in specific specs (NOT pre-seeded users) */
export const TEST_EMAILS = {
  signUpMp: "e2e-signup-mp@veedoo.io" as TestEmail,
  nonExistent: "e2e-nonexistent@test.local" as TestEmail,
  doubleClick: "e2e-doubleclk@veedoo.io" as TestEmail,
  deleteAccount: "e2e-delete-test@test.local" as TestEmail,
  nonMpEmail: "e2e-random@test.local" as TestEmail,
} as const;

/**
 * Create a test user via Supabase Admin API.
 * Idempotent: returns existing user ID if already present.
 *
 * Pass a pre-fetched `existingUsersMap` to skip the listUsers() call
 * (used in global-setup for parallel batch creation).
 */
export async function createTestUser(
  admin: TestSupabaseAdmin,
  user: TestUser,
  existingUsersMap?: Map<string, string>
): Promise<string> {
  // Resolve existing user ID — from map or via listUsers()
  let existingId: string | undefined;
  if (existingUsersMap) {
    existingId = existingUsersMap.get(user.email);
  } else {
    const { data } = await admin.auth.admin.listUsers({ perPage: 1000 });
    if (data?.users.length === 1000) {
      console.warn("[E2E] listUsers returned 1000 users — pagination may be truncating results");
    }
    existingId = data?.users.find((u) => u.email === user.email)?.id;
  }

  if (existingId) {
    await Promise.all([
      admin.from("user_roles").upsert(
        {
          user_id: existingId,
          email: user.email,
          role: user.role,
          is_first_login: user.isFirstLogin ?? false,
          ...(user.isFirstLogin ? { member_id: null } : {}),
        },
        { onConflict: "user_id" }
      ),
      admin.auth.admin.updateUserById(existingId, {
        user_metadata: {
          is_first_login: user.isFirstLogin ?? false,
          is_parliament_member: user.isParliamentMember ?? false,
          ...user.userMetadata,
        },
      }),
    ]);
    return existingId;
  }

  const { data, error } = await admin.auth.admin.createUser({
    email: user.email,
    email_confirm: true,
    user_metadata: {
      is_first_login: user.isFirstLogin ?? false,
      is_parliament_member: user.isParliamentMember ?? false,
      ...user.userMetadata,
    },
  });

  if (error) {
    throw new Error(
      `Failed to create test user ${user.email}: ${error.message}`
    );
  }

  await admin.from("user_roles").upsert(
    {
      user_id: data.user.id,
      email: user.email,
      role: user.role,
      is_first_login: user.isFirstLogin ?? false,
    },
    { onConflict: "user_id" }
  );

  return data.user.id;
}
