import type { TestSupabaseAdmin } from "./supabase-admin";
import { cleanupTestParliamentData } from "./factories/parliament-member-factory";
import { cleanupTestTeams } from "./factories/team-factory";
import { E2E_EMAIL_PREFIX, E2E_TEST_DOMAINS } from "./constants";

/**
 * Safety check: only allow deletion of test emails.
 */
function isTestEmail(email: string): boolean {
  return (
    email.startsWith(E2E_EMAIL_PREFIX) &&
    E2E_TEST_DOMAINS.some((domain) => email.endsWith(`@${domain}`))
  );
}

/**
 * Clean up a specific test user by email.
 * Refuses to delete non-test emails for safety.
 */
export async function cleanupTestUser(
  admin: TestSupabaseAdmin,
  email: string
): Promise<void> {
  if (!isTestEmail(email)) {
    throw new Error(`Refusing to delete non-test user: ${email}`);
  }

  // Targeted lookup via user_roles table (avoids listUsers(1000) full scan)
  const { data: roleData } = await admin
    .from("user_roles")
    .select("user_id")
    .eq("email", email)
    .maybeSingle();
  const userId = roleData?.user_id;

  if (!userId) {
    // Fallback: user may exist in auth but not in user_roles (orphaned)
    const { data } = await admin.auth.admin.listUsers({ perPage: 1000 });
    const orphaned = data?.users.find((u) => u.email === email);
    if (orphaned) await admin.auth.admin.deleteUser(orphaned.id);
    return;
  }

  // Clean up related data in parallel (no FK deps between these tables)
  await Promise.all([
    admin.from("user_clips").delete().eq("user_id", userId),
    admin.from("team_members").delete().eq("user_id", userId),
    admin.from("team_invitations").delete().eq("invited_by", userId),
    admin.from("team_invitations").delete().eq("accepted_by", userId),
    admin.from("user_roles").delete().eq("user_id", userId),
  ]);
  // Delete teams owned by this user (teams.owner_id has ON DELETE RESTRICT)
  await admin.from("teams").delete().eq("owner_id", userId);
  await admin.auth.admin.deleteUser(userId);
}

/**
 * Clean up ALL test users matching the e2e-* prefix.
 * Used in global teardown.
 */
export async function cleanupAllTestUsers(
  admin: TestSupabaseAdmin
): Promise<void> {
  const { data } = await admin.auth.admin.listUsers({ perPage: 1000 });
  if (!data?.users) return;
  if (data.users.length === 1000) {
    console.warn("[E2E] listUsers returned 1000 users — pagination may be truncating results");
  }

  const testUsers = data.users.filter(
    (u) => u.email && isTestEmail(u.email)
  );

  // Batch: delete related data for all test users in parallel
  const userIds = testUsers.map((u) => u.id);

  if (userIds.length > 0) {
    await Promise.all([
      admin.from("user_clips").delete().in("user_id", userIds),
      admin.from("team_members").delete().in("user_id", userIds),
      admin.from("team_invitations").delete().in("invited_by", userIds),
      admin.from("team_invitations").delete().in("accepted_by", userIds),
      admin.from("user_roles").delete().in("user_id", userIds),
    ]);

    // Delete teams owned by test users (teams.owner_id has ON DELETE RESTRICT)
    await admin.from("teams").delete().in("owner_id", userIds);

    // Delete auth users in parallel
    await Promise.all(testUsers.map((user) => admin.auth.admin.deleteUser(user.id)));
  }
}

/**
 * Clean up the app review user created by signInWithAppReviewPassword.
 * Bypasses the e2e- prefix check since the review email is not a test email.
 */
export async function cleanupAppReviewUser(
  admin: TestSupabaseAdmin,
  email: string
): Promise<void> {
  const { data: roleData } = await admin
    .from("user_roles")
    .select("user_id")
    .eq("email", email)
    .maybeSingle();

  if (!roleData?.user_id) {
    // Fallback: user may exist in auth but not in user_roles
    const { data } = await admin.auth.admin.listUsers({ perPage: 1000 });
    const orphaned = data?.users.find((u) => u.email === email);
    if (orphaned) await admin.auth.admin.deleteUser(orphaned.id);
    return;
  }

  const userId = roleData.user_id;
  await Promise.all([
    admin.from("user_clips").delete().eq("user_id", userId),
    admin.from("team_members").delete().eq("user_id", userId),
    admin.from("team_invitations").delete().eq("invited_by", userId),
    admin.from("team_invitations").delete().eq("accepted_by", userId),
    admin.from("user_roles").delete().eq("user_id", userId),
  ]);
  await admin.from("teams").delete().eq("owner_id", userId);
  await admin.auth.admin.deleteUser(userId);
}

/**
 * Full cleanup: all test data including parliament members, clips, teams, and users.
 * Used in global teardown.
 */
export async function cleanupAllTestData(
  admin: TestSupabaseAdmin
): Promise<void> {
  // Teams and parliament data are independent — clean in parallel
  // Only cleanupAllTestUsers must follow (users may own teams)
  await Promise.all([cleanupTestTeams(admin), cleanupTestParliamentData(admin)]);
  await cleanupAllTestUsers(admin);
}
