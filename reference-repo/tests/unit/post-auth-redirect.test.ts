import assert from "node:assert/strict";
import Module from "node:module";
import type { SupabaseClient, User } from "@supabase/supabase-js";

type ModuleLoad = (
  request: string,
  parent: NodeModule | null | undefined,
  isMain: boolean,
) => unknown;

const moduleWithLoad = Module as typeof Module & { _load: ModuleLoad };

function createSupabaseMock(teamMember: { team_id: string; role: string } | null) {
  return {
    from() {
      return {
        select() {
          return {
            eq() {
              return {
                order() {
                  return {
                    limit() {
                      return {
                        async maybeSingle() {
                          return { data: teamMember, error: null };
                        },
                      };
                    },
                  };
                },
              };
            },
          };
        },
      };
    },
  } as unknown as SupabaseClient;
}

async function main() {
  const originalLoad = moduleWithLoad._load;

  moduleWithLoad._load = function patchedLoad(
    request: string,
    parent: NodeModule | null | undefined,
    isMain: boolean,
  ) {
    if (request === "server-only") {
      return {};
    }

    return originalLoad(request, parent, isMain);
  };

  try {
    const { getPostAuthRedirectPath } = await import("@/lib/auth/post-auth-redirect");

    const baseUser = {
      id: "user_123",
      user_metadata: {
        is_first_login: true,
      },
    } as unknown as User;

    const teamlessSupabase = createSupabaseMock(null);

    // Stale invitationToken with failed acceptance (justAcceptedInvitation=false)
    // and no team_members row must NOT redirect to /team-setup — that page
    // would render with an empty teamId. Fall through to regular /setup.
    assert.equal(
      await getPostAuthRedirectPath(teamlessSupabase, baseUser, false, "invite_123", false),
      "/setup",
    );

    // When the invitation was actually accepted this session, redirect to /team-setup.
    assert.equal(
      await getPostAuthRedirectPath(teamlessSupabase, baseUser, false, "invite_123", true),
      "/team-setup",
    );

    assert.equal(
      await getPostAuthRedirectPath(teamlessSupabase, baseUser, true, null, false),
      "/mp-setup",
    );

    assert.equal(
      await getPostAuthRedirectPath(
        teamlessSupabase,
        {
          ...baseUser,
          user_metadata: {
            ...baseUser.user_metadata,
            is_first_login: true,
            is_team_member: true,
          },
        } as unknown as User,
        true,
        null,
        false,
      ),
      "/team-setup",
    );

    // Existing MP with team membership on regular login -> /dashboard
    const teamSupabase = createSupabaseMock({ team_id: "team_42", role: "member" });
    const existingUser = {
      id: "user_456",
      user_metadata: { is_first_login: false },
    } as unknown as User;

    assert.equal(
      await getPostAuthRedirectPath(teamSupabase, existingUser, true, null, false),
      "/dashboard",
      "MP on regular login should go to /dashboard even with team membership",
    );

    // Existing MP who just accepted an invitation -> /dashboard/teams/{id}
    assert.equal(
      await getPostAuthRedirectPath(teamSupabase, existingUser, true, null, true),
      "/dashboard/teams/team_42",
      "MP who just accepted invitation should go to team dashboard",
    );

    // Non-MP team member always goes to team dashboard
    assert.equal(
      await getPostAuthRedirectPath(teamSupabase, existingUser, false, null, false),
      "/dashboard/teams/team_42",
      "Non-MP team member should always go to team dashboard",
    );
  } finally {
    moduleWithLoad._load = originalLoad;
  }

  console.log("post-auth-redirect checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
