import fs from "fs";
import path from "path";
import { createTestSupabaseAdmin } from "./e2e/helpers/supabase-admin";
import {
  createTestUser,
  TEST_USERS,
  MAX_WORKERS,
  PLAYWRIGHT_PROJECTS,
  getProjectEmail,
  getProjectKey,
  getProjectWorkerEmail,
  getProjectWorkerKey,
  type TestUser,
} from "./e2e/helpers/test-users";
import { clearMailbox } from "./e2e/helpers/mailpit";
import {
  MP_ALPHA_ID,
  MP_BETA_ID,
  MP_GAMMA_ID,
  MP_LD_DELTA_ID,
} from "./e2e/helpers/constants";
import {
  createTestParliamentMember,
  createTestParliamentMemberContact,
  createTestParliamentMemberPortrait,
  createTestParliamentEvent,
  cleanupTestParliamentData,
} from "./e2e/helpers/factories/parliament-member-factory";
import {
  createTestParliamentMemberClip,
  createTestUserClip,
} from "./e2e/helpers/factories/clip-factory";
import { createTestTeam, createTestTeamMember, cleanupTestTeams } from "./e2e/helpers/factories/team-factory";

async function globalSetup() {
  console.log("[Global Setup] Starting...");

  // Clear stale auth cache so fixtures always generate fresh sessions
  const authStatesDir = path.join(__dirname, ".auth-states");
  if (fs.existsSync(authStatesDir)) {
    fs.rmSync(authStatesDir, { recursive: true, force: true });
    console.log("[Global Setup] Cleared stale .auth-states/");
  }

  // Safety: refuse to run against non-local Supabase
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
  if (!supabaseUrl.includes("localhost") && !supabaseUrl.includes("127.0.0.1")) {
    throw new Error(
      `[Global Setup] SUPABASE_URL does not point to localhost: ${supabaseUrl}\n` +
      "Refusing to run E2E setup against a non-local Supabase instance."
    );
  }

  const admin = createTestSupabaseAdmin();

  // ── Step 0: Clean up stale test data from previous runs ─────────
  // Prevents duplicate key violations when re-running without teardown
  // Order: user_clips → parliament_member_clips → teams → parliament data (FK deps)
  console.log("[Global Setup] Cleaning up stale test data...");
  await Promise.all([
    admin.from("user_clips").delete().like("title", "E2E%"),
    cleanupTestTeams(admin),
    cleanupTestParliamentData(admin),
  ]);

  // ── Step 1: Seed parliament data FIRST ──────────────────────────
  // Must run before creating users: the DB trigger on user creation
  // sets member_id on user_roles for parliament members, which has a
  // FK constraint on parliament_members.
  console.log("[Global Setup] Seeding parliament data...");

  // Parliament members
  // NOTE: member_id 5296 is hardcoded in the handle_new_user DB trigger
  // for @veedoo.io emails. Must exist before creating veedoo.io test users.
  await Promise.all([
    createTestParliamentMember(admin, {
      member_id: 5296,
      display_name: "E2E Veedoo Default MP",
      party_name: "Labour",
      party_abbreviation: "LAB",
      constituency_name: "Test Default",
    }),
    createTestParliamentMember(admin, {
      member_id: MP_ALPHA_ID,
      display_name: "E2E Test MP Alpha",
      party_name: "Labour",
      party_abbreviation: "LAB",
      constituency_name: "Test North",
    }),
    createTestParliamentMember(admin, {
      member_id: MP_BETA_ID,
      display_name: "E2E Test MP Beta",
      party_name: "Conservative",
      party_abbreviation: "CON",
      constituency_name: "Test South",
    }),
    createTestParliamentMember(admin, {
      member_id: MP_GAMMA_ID,
      display_name: "E2E Test MP Gamma",
      party_name: "Liberal Democrats",
      party_abbreviation: "LD",
      party_id: 17,
      constituency_name: "Test East",
    }),
    createTestParliamentMember(admin, {
      member_id: MP_LD_DELTA_ID,
      display_name: "E2E Test MP LD Delta",
      party_name: "Liberal Democrats",
      party_abbreviation: "LD",
      party_id: 17,
      constituency_name: "Test West",
    }),
  ]);

  // Portraits for all 3
  await Promise.all([
    createTestParliamentMemberPortrait(admin, { member_id: MP_ALPHA_ID }),
    createTestParliamentMemberPortrait(admin, { member_id: MP_BETA_ID }),
    createTestParliamentMemberPortrait(admin, { member_id: MP_GAMMA_ID }),
    createTestParliamentMemberPortrait(admin, { member_id: MP_LD_DELTA_ID }),
  ]);

  // Contact for MP user (links @veedoo.io email to member)
  await createTestParliamentMemberContact(admin, {
    member_id: MP_ALPHA_ID,
    email: TEST_USERS.mpUser.email,
  });

  // Parliament event
  const event = await createTestParliamentEvent(admin);

  // ── Step 2: Create test users in parallel ──────────────────────────
  // Runs after parliament data so FK constraints on member_id are satisfied
  console.log("[Global Setup] Creating test users...");

  const { data: existingData } = await admin.auth.admin.listUsers({ perPage: 1000 });
  if (existingData?.users.length === 1000) {
    console.warn("[Global Setup] listUsers returned 1000 users — pagination may be truncating results");
  }
  const existingUsersMap = new Map<string, string>(
    (existingData?.users ?? [])
      .filter((u) => !!u.email)
      .map((u) => [u.email!, u.id])
  );

  const userEntries = Object.entries(TEST_USERS) as [
    string,
    TestUser,
  ][];
  const userResults = await Promise.all(
    userEntries.map(async ([name, user]) => {
      const userId = await createTestUser(admin, user, existingUsersMap);
      console.log(
        `[Global Setup] Created/verified ${name}: ${user.email} (${userId})`
      );
      return [name, userId] as const;
    })
  );

  const userIds: Record<string, string> = {};
  for (const [name, userId] of userResults) {
    userIds[name] = userId;
  }

  // ── Step 2b: Create per-project+worker user variants ───────────────────
  // Each Playwright project + worker gets its own email for auth fixtures,
  // eliminating both cross-worker rate-limit collisions and cross-browser
  // state pollution on the same worker index.
  console.log("[Global Setup] Creating per-project user variants...");

  // Users that need project+worker variants (used by worker-scoped auth fixtures)
  const workerVariants: { baseName: string; baseUser: TestUser; needsMemberId: boolean; memberId?: number }[] = [
    { baseName: "regularUser", baseUser: TEST_USERS.regularUser, needsMemberId: true },
    { baseName: "adminUser", baseUser: TEST_USERS.adminUser, needsMemberId: false },
    { baseName: "mpCompletedUser", baseUser: TEST_USERS.mpCompletedUser, needsMemberId: true },
    { baseName: "ldMpUser", baseUser: TEST_USERS.ldMpUser, needsMemberId: true, memberId: MP_GAMMA_ID },
  ];
  const projectVariants: { baseName: string; baseUser: TestUser; needsMemberId: boolean }[] = [
    { baseName: "signinUser", baseUser: TEST_USERS.signinUser, needsMemberId: true },
  ];
  const setupWorkerVariants: {
    baseName: string;
    baseUser: TestUser;
    needsMemberId: boolean;
    needsParliamentContact?: boolean;
  }[] = [
    { baseName: "setupUser", baseUser: TEST_USERS.setupUser, needsMemberId: false },
    {
      baseName: "mpUser",
      baseUser: TEST_USERS.mpUser,
      needsMemberId: true,
      needsParliamentContact: true,
    },
    { baseName: "teamMember", baseUser: TEST_USERS.teamMember, needsMemberId: false },
    {
      baseName: "removedTeamMember",
      baseUser: TEST_USERS.removedTeamMember,
      needsMemberId: false,
    },
  ];

  // Refresh the existing users map (it may have new entries from Step 2)
  const { data: refreshedData } = await admin.auth.admin.listUsers({ perPage: 1000 });
  const refreshedMap = new Map<string, string>(
    (refreshedData?.users ?? [])
      .filter((u) => !!u.email)
      .map((u) => [u.email!, u.id])
  );

  for (const { baseName, baseUser } of workerVariants) {
    let createdCount = 0;
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      for (let i = 0; i < MAX_WORKERS; i++) {
        const workerEmail = getProjectWorkerEmail(baseUser.email, projectName, i);
        const workerUser: TestUser = {
          ...baseUser,
          email: workerEmail,
          isFirstLogin: false,
        };
        const userId = await createTestUser(admin, workerUser, refreshedMap);
        const key = getProjectWorkerKey(baseName, projectName, i);
        userIds[key] = userId;
        createdCount += 1;
      }
    }
    console.log(`[Global Setup] Created ${createdCount} per-project variants for ${baseName}`);
  }

  for (const { baseName, baseUser } of projectVariants) {
    let createdCount = 0;
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      const projectEmail = getProjectEmail(baseUser.email, projectName);
      const projectUser: TestUser = {
        ...baseUser,
        email: projectEmail,
      };
      const userId = await createTestUser(admin, projectUser, refreshedMap);
      userIds[getProjectKey(baseName, projectName)] = userId;
      createdCount += 1;
    }
    console.log(`[Global Setup] Created ${createdCount} per-project variants for ${baseName}`);
  }

  for (const { baseName, baseUser, needsParliamentContact } of setupWorkerVariants) {
    let createdCount = 0;
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      for (let i = 0; i < MAX_WORKERS; i++) {
        const workerEmail = getProjectWorkerEmail(baseUser.email, projectName, i);
        const workerUser: TestUser = {
          ...baseUser,
          email: workerEmail,
        };
        const userId = await createTestUser(admin, workerUser, refreshedMap);
        const key = getProjectWorkerKey(baseName, projectName, i);
        userIds[key] = userId;
        createdCount += 1;

        if (needsParliamentContact) {
          await createTestParliamentMemberContact(admin, {
            member_id: MP_ALPHA_ID,
            email: workerEmail,
          });
        }
      }
    }
    console.log(
      `[Global Setup] Created ${createdCount} per-project+worker setup variants for ${baseName}`
    );
  }

  // ── Step 3: Set up user_roles with correct member_id ───────────────
  // Regular user and mpCompletedUser need member_id for dashboard/clips
  const memberIdUpdates = [
    admin
      .from("user_roles")
      .update({ member_id: MP_ALPHA_ID })
      .eq("user_id", userIds.regularUser),
    admin
      .from("user_roles")
      .update({ member_id: MP_ALPHA_ID })
      .eq("user_id", userIds.mpCompletedUser),
    admin
      .from("user_roles")
      .update({ member_id: MP_ALPHA_ID })
      .eq("user_id", userIds.mpUser),
    admin
      .from("user_roles")
      .update({ member_id: MP_ALPHA_ID })
      .eq("user_id", userIds.signinUser),
    // LD MP user linked to MP_GAMMA_ID (party_id=17) for LD cross-party tests
    admin
      .from("user_roles")
      .update({ member_id: MP_GAMMA_ID })
      .eq("user_id", userIds.ldMpUser),
  ];

  // Also set member_id for per-worker variants that need it
  for (const { baseName, needsMemberId, memberId } of workerVariants) {
    if (!needsMemberId) continue;
    const targetMemberId = memberId ?? MP_ALPHA_ID;
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      for (let i = 0; i < MAX_WORKERS; i++) {
        const key = getProjectWorkerKey(baseName, projectName, i);
        if (userIds[key]) {
          memberIdUpdates.push(
            admin
              .from("user_roles")
              .update({ member_id: targetMemberId })
              .eq("user_id", userIds[key])
          );
        }
      }
    }
  }

  for (const { baseName, needsMemberId } of setupWorkerVariants) {
    if (!needsMemberId) continue;
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      for (let i = 0; i < MAX_WORKERS; i++) {
        const key = getProjectWorkerKey(baseName, projectName, i);
        if (userIds[key]) {
          memberIdUpdates.push(
            admin
              .from("user_roles")
              .update({ member_id: MP_ALPHA_ID })
              .eq("user_id", userIds[key])
          );
        }
      }
    }
  }

  for (const { baseName, needsMemberId } of projectVariants) {
    if (!needsMemberId) continue;
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      const key = getProjectKey(baseName, projectName);
      if (userIds[key]) {
        memberIdUpdates.push(
          admin
            .from("user_roles")
            .update({ member_id: MP_ALPHA_ID })
            .eq("user_id", userIds[key])
        );
      }
    }
  }

  await Promise.all(memberIdUpdates);

  // ── Step 4: Seed parliament member clips ──────────────────────────
  console.log("[Global Setup] Seeding clips...");

  const clipPromises = [];
  for (let i = 0; i < 5; i++) {
    clipPromises.push(
      createTestParliamentMemberClip(admin, {
        member_id: MP_ALPHA_ID,
        session_uid: event.event_id,
        session_date: event.session_date,
        transcript: `E2E test clip ${i + 1} transcript about parliament debate.`,
        description: i === 0
          ? "E2E healthcare funding debate summary"
          : `E2E test clip ${i + 1} description`,
      })
    );
  }
  const parliamentClips = await Promise.all(clipPromises);

  // Clips for MP Beta (Conservative) and MP Gamma (Liberal Democrats)
  await Promise.all([
    createTestParliamentMemberClip(admin, {
      member_id: MP_BETA_ID,
      session_uid: event.event_id,
      session_date: event.session_date,
      transcript: "E2E conservative MP clip about education policy.",
      description: "E2E Conservative education debate",
    }),
    createTestParliamentMemberClip(admin, {
      member_id: MP_BETA_ID,
      session_uid: event.event_id,
      session_date: event.session_date,
      transcript: "E2E conservative MP clip about tax reform.",
      description: "E2E Conservative tax debate",
    }),
    createTestParliamentMemberClip(admin, {
      member_id: MP_GAMMA_ID,
      session_uid: event.event_id,
      session_date: event.session_date,
      transcript: "E2E liberal democrat MP clip about climate change.",
      description: "E2E Liberal Democrat climate debate",
    }),
    createTestParliamentMemberClip(admin, {
      member_id: MP_LD_DELTA_ID,
      session_uid: event.event_id,
      session_date: event.session_date,
      transcript: "E2E liberal democrat delta MP clip about housing policy.",
      description: "E2E Liberal Democrat housing debate",
    }),
    createTestParliamentMemberClip(admin, {
      member_id: MP_LD_DELTA_ID,
      session_uid: event.event_id,
      session_date: event.session_date,
      transcript: "E2E liberal democrat delta MP clip about healthcare reform.",
      description: "E2E Liberal Democrat healthcare debate",
    }),
  ]);

  // ── Step 5: Seed user clips ───────────────────────────────────────
  console.log("[Global Setup] Seeding user clips...");

  const statuses = [
    "completed",
    "completed",
    "completed",
    "processing",
    "failed",
  ] as const;
  const userClipPromises = statuses.map((status, i) =>
    createTestUserClip(admin, {
      user_id: userIds.regularUser,
      clip_id: parliamentClips[i % parliamentClips.length].id,
      title: `E2E User Clip ${i + 1}`,
      status,
      ...(status === "failed" ? { error_message: "E2E test error" } : {}),
      ...(status === "processing"
        ? { clip_url: null, thumbnail_url: null }
        : {}),
    })
  );
  await Promise.all(userClipPromises);

  // Seed user clips for per-project regular user variants (same clips, different user_id)
  const workerClipPromises = [];
  for (const projectName of PLAYWRIGHT_PROJECTS) {
    for (let w = 0; w < MAX_WORKERS; w++) {
      const workerUserId = userIds[getProjectWorkerKey("regularUser", projectName, w)];
      if (!workerUserId) continue;
      for (let i = 0; i < statuses.length; i++) {
        const status = statuses[i];
        workerClipPromises.push(
          createTestUserClip(admin, {
            user_id: workerUserId,
            clip_id: parliamentClips[i % parliamentClips.length].id,
            title: `E2E User Clip ${i + 1}`,
            status,
            ...(status === "failed" ? { error_message: "E2E test error" } : {}),
            ...(status === "processing" ? { clip_url: null, thumbnail_url: null } : {}),
          })
        );
      }
    }
  }
  if (workerClipPromises.length > 0) {
    await Promise.all(workerClipPromises);
    console.log(`[Global Setup] Seeded ${workerClipPromises.length} per-project user clips`);
  }

  // ── Step 6: Seed team data ────────────────────────────────────────
  console.log("[Global Setup] Seeding team data...");

  const team = await createTestTeam(admin, {
    name: "E2E Test Team",
    owner_id: userIds.mpCompletedUser,
  });

  await createTestTeamMember(admin, {
    team_id: team.id,
    user_id: userIds.teamMember,
    role: "user",
  });

  // Add removedTeamMember to team, then remove — ensures team_members history exists
  await createTestTeamMember(admin, {
    team_id: team.id,
    user_id: userIds.removedTeamMember,
    role: "user",
  });
  await admin.from("team_members").delete().eq("user_id", userIds.removedTeamMember);

  for (const projectName of PLAYWRIGHT_PROJECTS) {
    for (let i = 0; i < MAX_WORKERS; i++) {
      const projectTeam = await createTestTeam(admin, {
        name: `E2E Test Team ${projectName} w${i}`,
        owner_id:
          userIds[getProjectWorkerKey("mpCompletedUser", projectName, i)] ??
          userIds.mpCompletedUser,
      });
      const projectTeamMemberId = userIds[getProjectWorkerKey("teamMember", projectName, i)];
      const projectRemovedTeamMemberId = userIds[getProjectWorkerKey(
        "removedTeamMember",
        projectName,
        i
      )];

      await createTestTeamMember(admin, {
        team_id: projectTeam.id,
        user_id: projectTeamMemberId,
        role: "user",
      });

      await createTestTeamMember(admin, {
        team_id: projectTeam.id,
        user_id: projectRemovedTeamMemberId,
        role: "user",
      });

      await admin
        .from("team_members")
        .delete()
        .eq("team_id", projectTeam.id)
        .eq("user_id", projectRemovedTeamMemberId);
    }
  }

  // ── Step 7: Clear mailboxes in parallel ───────────────────────────
  console.log("[Global Setup] Clearing mailboxes...");

  const mailboxes = Object.values(TEST_USERS).map((user) => clearMailbox(user.email));
  // Also clear per-project worker mailboxes
  for (const { baseUser } of workerVariants) {
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      for (let i = 0; i < MAX_WORKERS; i++) {
        mailboxes.push(clearMailbox(getProjectWorkerEmail(baseUser.email, projectName, i)));
      }
    }
  }
  for (const { baseUser } of projectVariants) {
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      mailboxes.push(clearMailbox(getProjectEmail(baseUser.email, projectName)));
    }
  }
  for (const { baseUser } of setupWorkerVariants) {
    for (const projectName of PLAYWRIGHT_PROJECTS) {
      for (let i = 0; i < MAX_WORKERS; i++) {
        mailboxes.push(clearMailbox(getProjectWorkerEmail(baseUser.email, projectName, i)));
      }
    }
  }
  await Promise.all(mailboxes);

  // ── Step 8: Write user IDs after all seeding completes ────────────
  // Written last so the file only exists when the full setup succeeded
  const idsPath = path.join(__dirname, ".test-user-ids.json");
  fs.writeFileSync(idsPath, JSON.stringify(userIds, null, 2));
  console.log(`[Global Setup] User IDs written to ${idsPath}`);

  // ── Step 9: Warm up Next.js dev server ──────────────────────────
  // Force-compile key routes before parallel workers hit them simultaneously
  console.log("[Global Setup] Warming up dev server...");
  const baseUrl =
    process.env.NEXT_PUBLIC_FRONTEND_URL ||
    "http://localhost:3001";
  for (const route of ["/signin", "/dashboard", "/setup", "/dashboard/all-clips", "/dashboard/ld-clips"]) {
    try {
      await fetch(`${baseUrl}${route}`, { redirect: "manual" });
    } catch {
      /* server may not be fully ready — that's OK */
    }
  }

  console.log("[Global Setup] Complete.");
}

export default globalSetup;
