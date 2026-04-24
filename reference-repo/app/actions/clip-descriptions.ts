"use server";

import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { ErrorLogger } from "@/lib/errorLogger";
import { generateAndFormatEmbedding } from "@/services/ai/embedding-service";
import { isMPEmail } from "@/lib/domains";

interface UpdateDescriptionResult {
  success: boolean;
  description?: string;
  hasEmbedding?: boolean;
  error?: string;
}

interface UpdateTranscriptResult {
  success: boolean;
  transcript?: string;
  error?: string;
}

/**
 * Server Action: Update clip description (manual editing only)
 * Note: Descriptions are auto-generated via embedding API when transcript embeddings are created.
 * This action is only for manual edits by users.
 */
export async function updateClipDescription(
  clipId: string,
  description: string
): Promise<UpdateDescriptionResult> {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user (using regular client for auth check)
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return { success: false, error: "Unauthorized" };
    }

    // Verify user email exists
    if (!user.email || typeof user.email !== 'string') {
      return { success: false, error: "User email not available" };
    }

    if (!clipId || typeof clipId !== "string") {
      return { success: false, error: "Clip ID is required" };
    }

    if (
      !description ||
      typeof description !== "string" ||
      description.trim().length === 0
    ) {
      return { success: false, error: "Description is required" };
    }

    const trimmedDescription = description.trim();

    // Verify clip exists - use admin client to bypass RLS
    const { data: clip, error: clipError } = await supabaseAdminClient
      .from("parliament_member_clips")
      .select("id, member_id")
      .eq("id", clipId)
      .eq("is_deleted", false)
      .single();

    if (clipError || !clip) {
      ErrorLogger.logDatabaseError(
        clipError,
        "Failed to fetch clip for description update",
        "parliament_member_clips",
        user.id
      );
      return { success: false, error: "Clip not found" };
    }

    // Get user's member_id and email
    const { data: userRole } = await supabaseAdminClient
      .from("user_roles")
      .select("member_id")
      .eq("user_id", user.id)
      .single();

    // Check personal mode permissions:
    // 1. User must have allowed MP domain email
    // 2. User's member_id must match clip's member_id (user follows that member)
    const isPersonalModeAllowed = 
      user.email && 
      isMPEmail(user.email) && 
      userRole?.member_id === clip.member_id;

    // Check team mode permissions:
    // 1. User must be owner or administrator of a team
    // 2. The team owner must follow the clip's member_id (checked via team_mp_follows and user_roles)
    let isTeamModeAllowed = false;
    
    if (!isPersonalModeAllowed) {
      // Get all teams where user is owner or administrator
      const { data: userTeams, error: teamsError } = await supabaseAdminClient
        .from("team_members")
        .select("team_id, role")
        .eq("user_id", user.id)
        .in("role", ["owner", "administrator"]);

      if (!teamsError && userTeams && userTeams.length > 0) {
        const teamIds = userTeams.map(t => t.team_id);
        
        // Get team owners for these teams
        const { data: teams, error: teamsDataError } = await supabaseAdminClient
          .from("teams")
          .select("id, owner_id")
          .in("id", teamIds)
          .eq("is_deleted", false);

        if (!teamsDataError && teams && teams.length > 0) {
          const teamOwnerIds = teams.map(t => t.owner_id);
          
          // Check if team owner follows this member (via user_roles.member_id)
          const { data: teamOwnerRoles, error: ownerRolesError } = await supabaseAdminClient
            .from("user_roles")
            .select("user_id, member_id")
            .in("user_id", teamOwnerIds)
            .eq("member_id", clip.member_id);

          // Also verify the team has the follow record in team_mp_follows
          const { data: teamFollows, error: followsError } = await supabaseAdminClient
            .from("team_mp_follows")
            .select("team_id")
            .in("team_id", teamIds)
            .eq("member_id", clip.member_id)
            .limit(1);

          // User can edit if:
          // - They are owner/admin of a team
          // - The team owner follows this member (user_roles check)
          // - The team has this member in team_mp_follows (team follow record exists)
          if (!ownerRolesError && teamOwnerRoles && teamOwnerRoles.length > 0 && 
              !followsError && teamFollows && teamFollows.length > 0) {
            isTeamModeAllowed = true;
          }
        }
      }
    }

    const canEdit = isPersonalModeAllowed || isTeamModeAllowed;

    if (!canEdit) {
      if (!user.email || !isMPEmail(user.email)) {
        return { success: false, error: "Only users with allowed MP domain emails can edit descriptions" };
      }
      if (userRole?.member_id !== clip.member_id) {
        return { success: false, error: "You can only edit descriptions for clips from members you follow" };
      }
      return { success: false, error: "You don't have permission to edit this clip's description" };
    }

    // Generate embedding for the updated description
    const embeddingResult = await generateAndFormatEmbedding(
      trimmedDescription
    );

    if (embeddingResult.error) {
      ErrorLogger.logError(
        new Error(embeddingResult.error ?? "Unknown error"),
        {
          userId: user.id,
          component: "ai-embedding",
          action: "generate-updated-description-embedding",
          additionalContext: {
            clipId,
            details: embeddingResult.error,
          },
        }
      );
      // Continue without embedding - better to have description than nothing
    }

    // Update clip with new description and embedding
    const { error: updateError } = await supabase
      .from("parliament_member_clips")
      .update({
        description: trimmedDescription,
        description_embedding: embeddingResult.error
          ? undefined
          : embeddingResult.data,
      })
      .eq("id", clipId);

    if (updateError) {
      ErrorLogger.logDatabaseError(
        updateError,
        "Failed to update description",
        "parliament_member_clips",
        user.id
      );
      return { success: false, error: "Failed to update description" };
    }

    return {
      success: true,
      description: trimmedDescription,
      hasEmbedding: !embeddingResult.error,
    };
  } catch (error) {
    ErrorLogger.logError(error, {
      component: "server-action",
      action: "updateClipDescription",
      additionalContext: { clipId },
    });
    return { success: false, error: "Internal server error" };
  }
}

/**
 * Server Action: Update clip transcript (manual editing only)
 */
export async function updateClipTranscript(
  clipId: string,
  transcript: string
): Promise<UpdateTranscriptResult> {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user (using regular client for auth check)
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return { success: false, error: "Unauthorized" };
    }

    // Verify user email exists
    if (!user.email || typeof user.email !== 'string') {
      return { success: false, error: "User email not available" };
    }

    if (!clipId || typeof clipId !== "string") {
      return { success: false, error: "Clip ID is required" };
    }

    if (
      !transcript ||
      typeof transcript !== "string" ||
      transcript.trim().length === 0
    ) {
      return { success: false, error: "Transcript is required" };
    }

    // Verify clip exists - use admin client to bypass RLS
    const { data: clip, error: clipError } = await supabaseAdminClient
      .from("parliament_member_clips")
      .select("id, member_id")
      .eq("id", clipId)
      .eq("is_deleted", false)
      .single();

    if (clipError || !clip) {
      ErrorLogger.logDatabaseError(
        clipError,
        "Failed to fetch clip for transcript update",
        "parliament_member_clips",
        user.id
      );
      return { success: false, error: "Clip not found" };
    }

    // Get user's member_id and email
    const { data: userRole } = await supabaseAdminClient
      .from("user_roles")
      .select("member_id")
      .eq("user_id", user.id)
      .single();

    // Check personal mode permissions:
    // 1. User must have allowed MP domain email
    // 2. User's member_id must match clip's member_id (user follows that member)
    const isPersonalModeAllowed = 
      user.email && 
      isMPEmail(user.email) && 
      userRole?.member_id === clip.member_id;

    // Check team mode permissions:
    // 1. User must be owner or administrator of a team
    // 2. The team owner must follow the clip's member_id (checked via team_mp_follows and user_roles)
    let isTeamModeAllowed = false;
    
    if (!isPersonalModeAllowed) {
      // Get all teams where user is owner or administrator
      const { data: userTeams, error: teamsError } = await supabaseAdminClient
        .from("team_members")
        .select("team_id, role")
        .eq("user_id", user.id)
        .in("role", ["owner", "administrator"]);

      if (!teamsError && userTeams && userTeams.length > 0) {
        const teamIds = userTeams.map(t => t.team_id);
        
        // Get team owners for these teams
        const { data: teams, error: teamsDataError } = await supabaseAdminClient
          .from("teams")
          .select("id, owner_id")
          .in("id", teamIds)
          .eq("is_deleted", false);

        if (!teamsDataError && teams && teams.length > 0) {
          const teamOwnerIds = teams.map(t => t.owner_id);
          
          // Check if team owner follows this member (via user_roles.member_id)
          const { data: teamOwnerRoles, error: ownerRolesError } = await supabaseAdminClient
            .from("user_roles")
            .select("user_id, member_id")
            .in("user_id", teamOwnerIds)
            .eq("member_id", clip.member_id);

          // Also verify the team has the follow record in team_mp_follows
          const { data: teamFollows, error: followsError } = await supabaseAdminClient
            .from("team_mp_follows")
            .select("team_id")
            .in("team_id", teamIds)
            .eq("member_id", clip.member_id)
            .limit(1);

          // User can edit if:
          // - They are owner/admin of a team
          // - The team owner follows this member (user_roles check)
          // - The team has this member in team_mp_follows (team follow record exists)
          if (!ownerRolesError && teamOwnerRoles && teamOwnerRoles.length > 0 && 
              !followsError && teamFollows && teamFollows.length > 0) {
            isTeamModeAllowed = true;
          }
        }
      }
    }

    const canEdit = isPersonalModeAllowed || isTeamModeAllowed;

    if (!canEdit) {
      if (!user.email || !isMPEmail(user.email)) {
        return { success: false, error: "Only users with allowed MP domain emails can edit transcripts" };
      }
      if (userRole?.member_id !== clip.member_id) {
        return { success: false, error: "You can only edit transcripts for clips from members you follow" };
      }
      return { success: false, error: "You don't have permission to edit this clip's transcript" };
    }

    // Validate transcript length
    const trimmedTranscript = transcript.trim();
    if (trimmedTranscript.length > 50000) {
      return {
        success: false,
        error: "Transcript must be 50,000 characters or less",
      };
    }

    // Update clip with new transcript and mark as manually edited
    const { error: updateError } = await supabase
      .from("parliament_member_clips")
      .update({
        transcript: trimmedTranscript,
        transcript_manually_edited: true,
      })
      .eq("id", clipId);

    if (updateError) {
      ErrorLogger.logDatabaseError(
        updateError,
        "Failed to update transcript",
        "parliament_member_clips",
        user.id
      );
      return { success: false, error: "Failed to update transcript" };
    }

    return {
      success: true,
      transcript: trimmedTranscript,
    };
  } catch (error) {
    ErrorLogger.logError(error, {
      component: "server-action",
      action: "updateClipTranscript",
      additionalContext: { clipId },
    });
    return { success: false, error: "Internal server error" };
  }
}
