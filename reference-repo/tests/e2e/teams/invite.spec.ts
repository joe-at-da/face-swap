import { randomUUID } from "node:crypto";
import { expect } from "@playwright/test";
import { injectSession, test } from "../fixtures/test-fixtures";
import { cleanupTestUser } from "../helpers/cleanup";
import {
  cleanupTestTeamById,
  createTestTeam,
  createTestTeamInvitation,
} from "../helpers/factories/team-factory";
import { createTestUser, type TestEmail } from "../helpers/test-users";

test.describe("Team Invitation", () => {
  test("direct accept requires terms checkbox and records acceptance", async ({
    page,
    supabaseAdmin,
    adminUser,
  }, testInfo) => {
    const inviteeEmail =
      `e2e-invite-accept-${testInfo.project.name}-${testInfo.parallelIndex}-${randomUUID().slice(0, 8)}@test.local` as TestEmail;
    let teamId: string | null = null;

    try {
      const inviteeUserId = await createTestUser(supabaseAdmin, {
        email: inviteeEmail,
        role: "user",
        isFirstLogin: false,
      });

      const team = await createTestTeam(supabaseAdmin, {
        owner_id: adminUser.userId,
        name: `E2E Invite Team ${Date.now()}`,
      });
      teamId = team.id;

      const token = `e2e-invite-${Date.now()}-${randomUUID().slice(0, 8)}`;
      await createTestTeamInvitation(supabaseAdmin, {
        email: inviteeEmail,
        invited_by: adminUser.userId,
        team_id: team.id,
        token,
      });

      await injectSession(page, supabaseAdmin, inviteeEmail);
      await page.goto(`/teams/invite/${token}`);

      const acceptButton = page.getByRole("button", { name: "Accept Invitation" });
      const termsCheckbox = page.locator('button[role="checkbox"]').first();

      await expect(acceptButton).toBeDisabled();
      await termsCheckbox.click();
      await expect(acceptButton).toBeEnabled();

      await acceptButton.click();
      await page.waitForURL(new RegExp(`/dashboard/teams/${team.id}`), {
        timeout: 30_000,
      });

      const { data: membership } = await supabaseAdmin
        .from("team_members")
        .select("team_id, user_id")
        .eq("team_id", team.id)
        .eq("user_id", inviteeUserId)
        .single();

      expect(membership).not.toBeNull();

      const { data: termsAcceptance } = await supabaseAdmin
        .from("terms_acceptances")
        .select("accepted_via, user_id")
        .eq("user_id", inviteeUserId)
        .single();

      expect(termsAcceptance).not.toBeNull();
      expect(termsAcceptance!.accepted_via).toBe("invite_direct");
    } finally {
      if (teamId) {
        await cleanupTestTeamById(supabaseAdmin, teamId);
      }
      await cleanupTestUser(supabaseAdmin, inviteeEmail);
    }
  });
});
