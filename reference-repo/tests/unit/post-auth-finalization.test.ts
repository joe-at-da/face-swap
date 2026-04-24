import assert from "node:assert/strict";
import { buildTermsErrorPath } from "@/lib/auth/terms-error-path";
import Module from "node:module";
import type { User } from "@supabase/supabase-js";

const inviteToken = "8b2c74d4-1b5f-4c4c-9f2e-1f6e3c9f4c6b-m1z4p2q";

assert.equal(
  buildTermsErrorPath(inviteToken),
  `/teams/invite/${encodeURIComponent(inviteToken)}`,
);
assert.equal(buildTermsErrorPath("abc/def"), "/signup");
assert.equal(buildTermsErrorPath(null), "/signup");

type PendingTerms = {
  invitationToken: string | null;
  requestedAt: string;
  surface: "invite_signup" | "invite_signin" | "signup";
};

type ModuleLoad = (
  request: string,
  parent: NodeModule | null | undefined,
  isMain: boolean,
) => unknown;

const moduleWithLoad = Module as typeof Module & { _load: ModuleLoad };

async function main() {
  process.env.NEXT_PUBLIC_FRONTEND_URL = "https://example.test";

  const originalLoad = moduleWithLoad._load;
  const inviteCalls: Array<unknown[]> = [];
  const updateUserCalls: Array<Record<string, unknown>> = [];
  const signOutCalls: Array<Record<string, unknown>> = [];
  let pendingTerms: PendingTerms | null = null;
  let recordedTermsAcceptance: Record<string, unknown> | null = null;
  let shouldRecordTermsSucceed = true;

  const supabaseAdminMock = {
    from() {
      return {
        select() {
          return {
            eq() {
              return {
                maybeSingle: async () => ({ data: recordedTermsAcceptance, error: null }),
              };
            },
          };
        },
      };
    },
  };

  const supabaseMock = {
    auth: {
      signOut: async (options: Record<string, unknown>) => {
        signOutCalls.push(options);
        return { error: null };
      },
      updateUser: async ({ data }: { data: Record<string, unknown> }) => {
        updateUserCalls.push(data);
        return { error: null };
      },
    },
  };

  moduleWithLoad._load = function patchedLoad(
    request: string,
    parent: NodeModule | null | undefined,
    isMain: boolean,
  ) {
    if (request === "server-only") {
      return {};
    }

    if (
      request === "@/supabase/supabaseAdmin" ||
      request.endsWith("/supabase/supabaseAdmin")
    ) {
      return { supabaseAdminClient: supabaseAdminMock };
    }

    if (request === "@/lib/user-helpers" || request.endsWith("/lib/user-helpers")) {
      return {
        isActualMP: async () => false,
      };
    }

    if (request === "@/lib/team-helpers" || request.endsWith("/lib/team-helpers")) {
      return {
        acceptTeamInvitation: async (...args: unknown[]) => {
          inviteCalls.push(args);
          return { success: true, teamId: "team-123", teamName: "Team 123" };
        },
      };
    }

    if (request === "@/lib/errorLogger" || request.endsWith("/lib/errorLogger")) {
      return {
        ErrorLogger: {
          logError() {},
          logDatabaseError() {},
          logAuthError() {},
        },
      };
    }

    if (
      request === "@/lib/auth/post-auth-redirect" ||
      request.endsWith("/lib/auth/post-auth-redirect")
    ) {
      return {
        getPostAuthRedirectPath: async (
          _supabase: unknown,
          user: { user_metadata?: Record<string, unknown> },
          _isActualMPUser: boolean,
          invitationToken: string | null,
          justAcceptedInvitation: boolean,
        ) => {
          if (justAcceptedInvitation || invitationToken) {
            return "/dashboard/teams/team-123";
          }

          const isFirstLogin = user.user_metadata?.is_first_login !== false;
          return isFirstLogin ? "/setup" : "/dashboard";
        },
      };
    }

    if (
      request === "@/lib/legal/terms" ||
      request.endsWith("/lib/legal/terms")
    ) {
      const metadataSurfaces = ["signup", "invite_signup", "invite_signin"];
      return {
        clearPendingTermsMetadata: () => ({}),
        getPendingTermsAcceptance: () => pendingTerms,
        isMetadataTermsSurface: (v: unknown) => typeof v === "string" && metadataSurfaces.includes(v),
        METADATA_TERMS_SURFACES: metadataSurfaces,
        recordTermsAcceptance: async () => shouldRecordTermsSucceed,
        signOutForTermsFailure: async (supabase: typeof supabaseMock) => {
          await supabase.auth.signOut({ scope: "global" });
          return true;
        },
        TERMS_METADATA_KEYS: {
          invitationToken: "terms_acceptance_invitation_token",
          pending: "terms_acceptance_pending",
          requestedAt: "terms_acceptance_requested_at",
          surface: "terms_acceptance_surface",
        },
        TERMS_PENDING_WINDOW_MS: 60 * 60 * 1000,
      };
    }

    if (
      request === "@/lib/auth/terms-error-path" ||
      request.endsWith("/lib/auth/terms-error-path")
    ) {
      return {
        buildTermsErrorPath: (token: string | null) =>
          token ? `/teams/invite/${encodeURIComponent(token)}` : "/signup",
      };
    }

    return originalLoad(request, parent, isMain);
  };

  try {
    const { finalizePostAuth } = await import("@/lib/auth/post-auth-finalization");

    const user = {
      id: "user-123",
      email: "invitee@example.test",
      created_at: new Date().toISOString(),
      user_metadata: {
        invitation_token: "invite-token-123",
        is_first_login: false,
      },
    } as unknown as User;

    // Stale invitation_token without terms metadata (rawPending undefined)
    // is NOT an active invitation flow — user passes through without terms block.
    const staleTokenResult = await finalizePostAuth(user, supabaseMock as never);
    assert.equal(staleTokenResult.ok, true);
    if (staleTokenResult.ok) {
      assert.equal(staleTokenResult.redirectTo, "/dashboard/teams/team-123");
    }
    assert.equal(inviteCalls.length, 1);
    assert.equal(signOutCalls.length, 0);
    assert.deepEqual(updateUserCalls[0]?.invitation_token, null);

    // Active invitation flow: rawPending === true triggers terms enforcement.
    // Without DB acceptance, the user is blocked.
    const activeInviteUser = {
      id: "active-invite-user",
      email: "active@example.test",
      created_at: new Date().toISOString(),
      user_metadata: {
        invitation_token: "invite-token-456",
        is_first_login: false,
        terms_acceptance_pending: true,
        terms_acceptance_surface: "invite_signin",
        terms_acceptance_requested_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      },
    } as unknown as User;

    pendingTerms = null;
    recordedTermsAcceptance = null;
    shouldRecordTermsSucceed = false;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const activeBlockedResult = await finalizePostAuth(activeInviteUser, supabaseMock as never);
    assert.equal(activeBlockedResult.ok, false);
    if (!activeBlockedResult.ok) {
      assert.equal(activeBlockedResult.errorCode, "terms_acceptance_failed");
    }
    assert.equal(inviteCalls.length, 0);
    assert.equal(signOutCalls.length, 1);

    // Same active invite user, but recordTermsAcceptance now succeeds
    pendingTerms = null;
    recordedTermsAcceptance = { accepted_via: "invite_signin", user_id: activeInviteUser.id };
    shouldRecordTermsSucceed = true;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const retriedResult = await finalizePostAuth(activeInviteUser, supabaseMock as never);
    assert.equal(retriedResult.ok, true);
    assert.equal(inviteCalls.length, 1);
    assert.deepEqual(updateUserCalls[0]?.invitation_token, null);

    const legacyUser = {
      id: "legacy-user-123",
      email: "legacy@example.test",
      created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      user_metadata: {},
    } as unknown as User;

    pendingTerms = null;
    recordedTermsAcceptance = null;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const legacyResult = await finalizePostAuth(legacyUser, supabaseMock as never);
    assert.equal(legacyResult.ok, true);
    if (legacyResult.ok) {
      assert.equal(legacyResult.redirectTo, "/setup");
    }
    assert.equal(inviteCalls.length, 0);
    assert.equal(signOutCalls.length, 0);
    assert.equal(updateUserCalls[0]?.is_first_login, true);

    // --- Step 10: recordTermsAcceptance DB failure ---
    const termsFailUser = {
      id: "terms-fail-user",
      email: "termsfail@example.test",
      created_at: new Date().toISOString(),
      user_metadata: {
        is_first_login: true,
      },
    } as unknown as User;

    pendingTerms = {
      invitationToken: null,
      requestedAt: new Date().toISOString(),
      surface: "signup" as const,
    };
    shouldRecordTermsSucceed = false;
    recordedTermsAcceptance = null;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const termsFailResult = await finalizePostAuth(termsFailUser, supabaseMock as never);
    assert.equal(termsFailResult.ok, false);
    if (!termsFailResult.ok) {
      assert.equal(termsFailResult.errorCode, "terms_acceptance_failed");
    }
    assert.equal(signOutCalls.length, 1);
    assert.equal(inviteCalls.length, 0);

    // --- Step 11: expired terms consent recovery ---
    const expiredConsentUser = {
      id: "expired-consent-user",
      email: "expired@example.test",
      created_at: new Date().toISOString(),
      user_metadata: {
        is_first_login: true,
        terms_acceptance_pending: true,
        terms_acceptance_surface: "signup",
        terms_acceptance_requested_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      },
    } as unknown as User;

    pendingTerms = null;
    shouldRecordTermsSucceed = true;
    recordedTermsAcceptance = null;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const expiredConsentResult = await finalizePostAuth(expiredConsentUser, supabaseMock as never);
    assert.equal(expiredConsentResult.ok, true);
    if (expiredConsentResult.ok) {
      assert.equal(expiredConsentResult.redirectTo, "/setup");
    }
    assert.equal(signOutCalls.length, 0);

    // --- Step 12: recent legacy user without terms metadata ---
    // A pre-existing user created less than 1 hour ago (before terms
    // enforcement was deployed) should NOT be locked out. Detection is
    // based on absence of terms_acceptance_pending metadata, not age.
    const recentLegacyUser = {
      id: "recent-legacy-user",
      email: "recent-legacy@example.test",
      created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
      user_metadata: {},
    } as unknown as User;

    pendingTerms = null;
    shouldRecordTermsSucceed = true;
    recordedTermsAcceptance = null;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const recentLegacyResult = await finalizePostAuth(recentLegacyUser, supabaseMock as never);
    assert.equal(recentLegacyResult.ok, true);
    if (recentLegacyResult.ok) {
      assert.equal(recentLegacyResult.redirectTo, "/setup");
    }
    assert.equal(signOutCalls.length, 0);
    assert.equal(updateUserCalls[0]?.is_first_login, true);

    // --- Step 13: new user with cleared terms metadata (null) must NOT bypass terms ---
    // signInWithOtp clears pending terms metadata for non-invite sign-ins,
    // setting terms_acceptance_pending to null. This explicit null must NOT
    // be treated as a legacy user (whose key is undefined / never set).
    const clearedMetadataUser = {
      id: "cleared-metadata-user",
      email: "cleared@example.test",
      created_at: new Date().toISOString(),
      user_metadata: {
        is_first_login: true,
        terms_acceptance_pending: null,
        terms_acceptance_surface: null,
        terms_acceptance_requested_at: null,
        terms_acceptance_invitation_token: null,
      },
    } as unknown as User;

    pendingTerms = null;
    shouldRecordTermsSucceed = true;
    recordedTermsAcceptance = null;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const clearedResult = await finalizePostAuth(clearedMetadataUser, supabaseMock as never);
    assert.equal(clearedResult.ok, false);
    if (!clearedResult.ok) {
      assert.equal(clearedResult.errorCode, "terms_acceptance_required");
    }
    assert.equal(signOutCalls.length, 1);
    assert.equal(inviteCalls.length, 0);

    // --- Step 14: returning first-login user with cleared metadata but DB acceptance ---
    // A user who signed up, accepted terms (recorded in DB), verified OTP
    // (metadata cleared to null), but never completed setup (is_first_login
    // still true). On next sign-in, metadata is null — but the DB row proves
    // they already consented. They must NOT be locked out.
    const returningFirstLoginUser = {
      id: "returning-first-login-user",
      email: "returning@example.test",
      created_at: new Date().toISOString(),
      user_metadata: {
        is_first_login: true,
        terms_acceptance_pending: null,
        terms_acceptance_surface: null,
        terms_acceptance_requested_at: null,
        terms_acceptance_invitation_token: null,
      },
    } as unknown as User;

    pendingTerms = null;
    shouldRecordTermsSucceed = true;
    recordedTermsAcceptance = { user_id: returningFirstLoginUser.id };
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const returningResult = await finalizePostAuth(returningFirstLoginUser, supabaseMock as never);
    assert.equal(returningResult.ok, true);
    if (returningResult.ok) {
      assert.equal(returningResult.redirectTo, "/setup");
    }
    assert.equal(signOutCalls.length, 0);
    assert.equal(inviteCalls.length, 0);
    assert.equal(updateUserCalls[0]?.is_first_login, true);

    // --- Step 15: legacy user with stale invitation_token must NOT be locked out ---
    // A pre-existing user who once started an invitation flow but never completed it
    // has a stale invitation_token in metadata but no terms_acceptance_pending.
    // The stale token must NOT trigger terms enforcement (lines 149/158 use
    // isActiveInvitationFlow, not invitationToken).
    const staleInviteUser = {
      id: "stale-invite-user",
      email: "stale-invite@example.test",
      created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      user_metadata: {
        invitation_token: "stale-token-from-old-invite",
      },
    } as unknown as User;

    pendingTerms = null;
    shouldRecordTermsSucceed = true;
    recordedTermsAcceptance = null;
    signOutCalls.length = 0;
    inviteCalls.length = 0;
    updateUserCalls.length = 0;

    const staleInviteResult = await finalizePostAuth(staleInviteUser, supabaseMock as never);
    assert.equal(staleInviteResult.ok, true);
    if (staleInviteResult.ok) {
      assert.equal(staleInviteResult.redirectTo, "/dashboard/teams/team-123");
    }
    assert.equal(signOutCalls.length, 0);
    // Stale token still triggers acceptTeamInvitation (may fail gracefully)
    assert.equal(inviteCalls.length, 1);
  } finally {
    moduleWithLoad._load = originalLoad;
  }

  console.log("post-auth-finalization path checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
