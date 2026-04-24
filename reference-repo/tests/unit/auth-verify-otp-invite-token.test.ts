import assert from "node:assert/strict";
import Module from "node:module";

type ModuleLoad = (
  request: string,
  parent: NodeModule | null | undefined,
  isMain: boolean,
) => unknown;

const moduleWithLoad = Module as typeof Module & { _load: ModuleLoad };

async function main() {
  const originalLoad = moduleWithLoad._load;
  const verifyOtpCalls: Array<Record<string, unknown>> = [];
  let finalizedUser: { user_metadata?: Record<string, unknown> } | null = null;

  const supabaseMock = {
    auth: {
      verifyOtp: async (args: Record<string, unknown>) => {
        verifyOtpCalls.push(args);
        return {
          data: {
            user: {
              id: "user-123",
              email: "invitee@example.test",
              created_at: "2025-03-27T00:00:00.000Z",
              user_metadata: {
                is_first_login: false,
                invitation_token: "invite-token-123",
              },
            },
          },
          error: null,
        };
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
      request === "@/supabase/supabaseServerClient" ||
      request.endsWith("/supabase/supabaseServerClient")
    ) {
      return {
        createSupabaseServerClient: async () => supabaseMock,
      };
    }

    if (
      request === "@/supabase/supabaseAdmin" ||
      request.endsWith("/supabase/supabaseAdmin")
    ) {
      return {
        supabaseAdminClient: {},
      };
    }

    if (request === "@/lib/domains" || request.endsWith("/lib/domains")) {
      return {
        isMPEmail: () => false,
        getMPDomainsForDisplay: () => "test",
      };
    }

    if (request === "@/lib/user-helpers" || request.endsWith("/lib/user-helpers")) {
      return {
        isActualMPByEmail: async () => false,
      };
    }

    if (request === "@/lib/errorLogger" || request.endsWith("/lib/errorLogger")) {
      return {
        ErrorLogger: {
          logEvent() {},
          logAuthError() {},
          logDatabaseError() {},
          logClientError() {},
          logError() {},
        },
      };
    }

    if (request === "@/lib/team-helpers" || request.endsWith("/lib/team-helpers")) {
      return {
        acceptTeamInvitation: async () => ({ success: true }),
      };
    }

    if (
      request === "@/lib/legal/terms" ||
      request.endsWith("/lib/legal/terms")
    ) {
      return {
        TERMS_METADATA_KEYS: {
          invitationToken: "terms_acceptance_invitation_token",
          pending: "terms_acceptance_pending",
          requestedAt: "terms_acceptance_requested_at",
          surface: "terms_acceptance_surface",
        },
        buildPendingTermsMetadata: (
          surface: "signup" | "invite_signup" | "invite_signin",
          invitationToken?: string | null,
        ) => ({
          terms_acceptance_pending: true,
          terms_acceptance_surface: surface,
          terms_acceptance_requested_at: "2025-03-27T00:00:00.000Z",
          terms_acceptance_invitation_token: invitationToken ?? null,
        }),
        clearPendingTermsMetadata: () => ({}),
        getPendingTermsAcceptance: () => null,
        recordTermsAcceptance: async () => true,
        signOutForTermsFailure: async () => undefined,
        TERMS_PENDING_WINDOW_MS: 60 * 60 * 1000,
      };
    }

    if (
      request === "@/lib/auth/post-auth-finalization" ||
      request.endsWith("/lib/auth/post-auth-finalization")
    ) {
      return {
        finalizePostAuth: async (user: { user_metadata?: Record<string, unknown> }) => {
          finalizedUser = user;
          return { ok: true, redirectTo: "/dashboard" };
        },
      };
    }

    return originalLoad(request, parent, isMain);
  };

  try {
    const { verifyOtp } = await import("@/app/actions/auth");

    const result = await verifyOtp({
      email: "invitee@example.test",
      token: "123456",
      invitationToken: "invite-token-123",
    });

    assert.equal(result.success, true);
    assert.equal(result.redirectTo, "/dashboard");
    assert.equal(verifyOtpCalls.length, 1);
    assert.deepEqual(verifyOtpCalls[0], {
      email: "invitee@example.test",
      token: "123456",
      type: "email",
    });
    assert.ok(finalizedUser);
    if (!finalizedUser) {
      throw new Error("Expected finalizePostAuth to receive a user");
    }
    const restoredUser: { user_metadata?: Record<string, unknown> } = finalizedUser;
    assert.equal(restoredUser.user_metadata?.invitation_token, "invite-token-123");
    // When no pre-existing terms metadata is present, restoreInviteContextFromToken
    // must NOT synthesise pending terms — that would allow a terms bypass.
    assert.equal(restoredUser.user_metadata?.terms_acceptance_pending, undefined);
    assert.equal(restoredUser.user_metadata?.terms_acceptance_surface, undefined);
    assert.equal(restoredUser.user_metadata?.terms_acceptance_invitation_token, undefined);
  } finally {
    moduleWithLoad._load = originalLoad;
  }

  console.log("auth verifyOtp invite token checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
