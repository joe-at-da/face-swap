"use server";

import "server-only";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { acceptTeamInvitation } from "@/lib/team-helpers";
import { ErrorLogger } from "@/lib/errorLogger";
import { recordTermsAcceptance } from "@/lib/legal/terms";
import { z } from "zod";

export type AcceptInvitationError =
  | "INVALID_TOKEN"
  | "SESSION_EXPIRED"
  | "INVITATION_EXPIRED"
  | "EMAIL_MISMATCH"
  | "TERMS_REQUIRED"
  | "TERMS_RECORDING_FAILED"
  | "ACCEPTANCE_FAILED"
  | "UNEXPECTED_ERROR";

export type DirectAcceptResult =
  | { success: false; error: AcceptInvitationError }
  | { success: true; redirectTo: string };

const invitationTokenSchema = z.string().min(1).max(255);
const uuidSchema = z.string().uuid();

export async function acceptInvitationDirectly(
  token: string,
  acceptedTerms?: boolean,
): Promise<DirectAcceptResult> {
  try {
    const validated = invitationTokenSchema.safeParse(token);
    if (!validated.success) {
      return { success: false, error: "INVALID_TOKEN" };
    }

    if (acceptedTerms !== true) {
      return { success: false, error: "TERMS_REQUIRED" };
    }

    const supabase = await createSupabaseServerClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return { success: false, error: "SESSION_EXPIRED" };
    }

    // Re-verify email matches the invitation before calling acceptTeamInvitation.
    // The helper writes invitation_token into user metadata on failure, so if the
    // session changed (e.g. account switch in another tab) we must bail out here
    // to avoid stranding the wrong account with stale invite metadata.
    const { data: invitation, error: lookupError } = await supabaseAdminClient
      .from("team_invitations")
      .select("email, team_id")
      .eq("token", validated.data)
      .is("accepted_at", null)
      .gt("expires_at", new Date().toISOString())
      .single();

    if (lookupError && lookupError.code !== "PGRST116") {
      // Transient DB error — not a missing row. Log and surface as unexpected.
      ErrorLogger.logDatabaseError(lookupError, "acceptInvitationDirectly:precheck", "team_invitations");
      return { success: false, error: "UNEXPECTED_ERROR" };
    }

    if (!invitation) {
      return { success: false, error: "INVITATION_EXPIRED" };
    }

    if (invitation.email.toLowerCase() !== user.email?.toLowerCase()) {
      return { success: false, error: "EMAIL_MISMATCH" };
    }

    const recordedTerms = await recordTermsAcceptance(user.id, "invite_direct");
    if (!recordedTerms) {
      return { success: false, error: "TERMS_RECORDING_FAILED" };
    }

    const result = await acceptTeamInvitation(
      user.id,
      user.email || "",
      validated.data,
      supabaseAdminClient,
      supabase,
    );

    if (!result.success) {
      // acceptTeamInvitation writes invitation_token/invitation_failed into user
      // metadata on failure. For the direct-accept path this is stale — clean it up
      // to prevent /team-setup from treating this user as mid-invitation.
      const { error: cleanupError } = await supabase.auth.updateUser({
        data: { invitation_token: null, invitation_failed: null, invitation_message: null },
      });
      if (cleanupError) {
        ErrorLogger.logError(
          new Error(`Failed to clear stale invitation metadata: ${cleanupError.message}`),
          { action: "acceptInvitationDirectly:metadataCleanup", feature: "team_invitations" },
        );
      }

      // "Already a team member" — redirect to the invited team's dashboard.
      // Use invitation.team_id (from the precheck) to avoid redirecting to the
      // wrong team when the user belongs to multiple teams.
      if (result.message?.includes("Already a team member")) {
        const validId = uuidSchema.safeParse(invitation.team_id);
        if (validId.success) {
          return { success: true, redirectTo: `/dashboard/teams/${validId.data}` };
        }
      }

      ErrorLogger.logError(
        new Error(`Direct invitation acceptance failed: ${result.message}`),
        {
          action: "acceptInvitationDirectly",
          feature: "team_invitations",
        },
      );
      return { success: false, error: "ACCEPTANCE_FAILED" };
    }

    const validTeamId = uuidSchema.safeParse(result.teamId);
    if (!validTeamId.success) {
      return { success: false, error: "UNEXPECTED_ERROR" };
    }

    return {
      success: true,
      redirectTo: `/dashboard/teams/${validTeamId.data}`,
    };
  } catch (error) {
    ErrorLogger.logError(
      error instanceof Error ? error : new Error(String(error)),
      { action: "acceptInvitationDirectly", feature: "team_invitations" },
    );
    return { success: false, error: "UNEXPECTED_ERROR" };
  }
}
