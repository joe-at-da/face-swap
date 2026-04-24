"use server";

import {
  getConnectSocialMediaAccounts,
  createPostizPost,
  getNextAvailableSlot,
} from "@/services/postiz/postizApi";
import { createBlueskyPostWithVideo } from "@/services/bluesky/blueskyApi";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { captureServerEvent } from "@/lib/posthog-server";
import { getMPTrackingContext } from "@/lib/posthog-helpers";
import { isFacebookAllowed } from "@/lib/facebookAllowlist";

/**
 * Map platform identifier to database column name
 */
function getPlatformColumnName(identifier: string): string {
  const mapping: Record<string, string> = {
    x: "twitter_post_ids",
    linkedin: "linkedin_post_ids",
    "linkedin-page": "linkedin_page_post_ids",
    instagram: "instagram_post_ids",
    "instagram-standalone": "instagram_standalone_post_ids",
    facebook: "facebook_post_ids",
    threads: "threads_post_ids",
    youtube: "youtube_post_ids",
    tiktok: "tiktok_post_ids",
    mastodon: "mastodon_post_ids",
    bluesky: "bluesky_post_ids",
  };
  return mapping[identifier] || `${identifier}_post_ids`;
}

/**
 * Get team owner's connected social media accounts
 * @param teamId - Team ID to get owner's accounts for
 * @returns List of connected platforms or error
 */
export async function getTeamOwnerSocialMediaAccountsAction(teamId: string) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Verify user is a member of the team
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId,
    });

    if (!userRole) {
      return {
        error: "You are not a member of this team",
        data: null,
      };
    }

    // Get team and team owner
    const { data: team, error: teamError } = await supabaseAdminClient
      .from("teams")
      .select("owner_id, name")
      .eq("id", teamId)
      .single();

    if (teamError || !team) {
      throw new Error("Team not found");
    }

    // Get team owner's Postiz and Bluesky credentials (including cached profile data)
    const { data: ownerRole, error: ownerRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select(
        "postiz_email, username, email, bluesky_service, bluesky_identifier, bluesky_password, bluesky_avatar, bluesky_display_name"
      )
      .eq("user_id", team.owner_id)
      .single();

    // Handle case where team owner doesn't have a user_roles record yet
    if (ownerRoleError) {
      // PGRST116 = No rows found - team owner hasn't completed setup
      if (ownerRoleError.code === "PGRST116") {
        return {
          error: null,
          data: [],
          postizNotSetup: true,
          ownerName: "Team Owner",
        };
      }
      // Real database error - throw it
      throw new Error(`Failed to fetch team owner role: ${ownerRoleError.message}`);
    }

    if (!ownerRole) {
      return {
        error: "Team owner not found",
        data: null,
        postizNotSetup: true,
        ownerName: "Team Owner",
      };
    }

    const postizEmail = ownerRole.postiz_email;

    // If Postiz account not created for team owner
    if (!postizEmail) {
      return {
        error: null,
        data: [],
        postizNotSetup: true,
        ownerName: ownerRole.username || ownerRole.email || "Team Owner",
      };
    }

    // Get Postiz platforms using team owner's credentials
    let platforms: Array<{
      name: string;
      identifier: string;
      isConnected: boolean;
      integrationId?: string;
      profile?: string;
      profileName?: string;
      picture?: string;
    }> = [];

    const response = await getConnectSocialMediaAccounts(postizEmail);
    if (!response.error && response.data) {
      // Filter out Bluesky (handled via AT Protocol) and restricted platforms
      const facebookAllowed = isFacebookAllowed(user.email ?? "");
      platforms = response.data.filter(
        (p: { identifier: string }) =>
          p.identifier !== "bluesky" &&
          (p.identifier !== "facebook" || facebookAllowed)
      );
    }

    // Check if team owner has Bluesky credentials (stored separately from Postiz)
    // Use cached profile data (avatar, display_name) to avoid API calls on every poll
    if (
      ownerRole.bluesky_service &&
      ownerRole.bluesky_identifier &&
      ownerRole.bluesky_password
    ) {
      platforms.push({
        name: "Bluesky",
        identifier: "bluesky",
        isConnected: true,
        integrationId: "bluesky-direct",
        profile: ownerRole.bluesky_identifier,
        profileName: ownerRole.bluesky_display_name || ownerRole.bluesky_identifier,
        picture: ownerRole.bluesky_avatar || undefined,
      });
    }

    return {
      error: null,
      data: platforms,
      ownerName: ownerRole.username || ownerRole.email || "Team Owner",
    };
  } catch (error) {
    console.error("Error getting team owner social media accounts:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Get team owner's OAuth URL for connecting a platform
 * This is used when team members want to view which platforms are available
 * but only team owner can actually connect new platforms
 * @param teamId - Team ID
 * @param platform - Platform identifier
 * @returns Message indicating owner must connect
 */
export async function getTeamOwnerOAuthUrlAction(
  teamId: string
) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Verify user is a member
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId,
    });

    if (!userRole) {
      return {
        error: "You are not a member of this team",
        data: null,
      };
    }

    return {
      error: "Only the team owner can connect social media accounts for the team",
      data: null,
    };
  } catch (error) {
    console.error("Error:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Create social media post using team owner's account
 * @param clipId - User clip ID
 * @param teamId - Team ID (to get owner credentials)
 * @param integrationIds - Array of integration IDs to post to
 * @param platforms - Array of platform identifiers
 * @param message - Post message/caption
 * @param mediaUrls - Array of media URLs
 * @param scheduleTime - Optional ISO 8601 datetime for scheduling
 * @returns Success or error with post IDs
 */
export async function createTeamSocialMediaPostAction(
  clipId: string,
  teamId: string,
  integrationIds: string[],
  platforms: string[],
  message: string,
  mediaUrls: string[],
  scheduleTime: string | null = null
) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Verify user is a member of the team
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId,
    });

    if (!userRole) {
      return {
        error: "You are not a member of this team",
        data: null,
      };
    }

    // Check if Bluesky is included in platforms
    const blueskyIndex = platforms.indexOf("bluesky");
    const hasBluesky = blueskyIndex !== -1;

    // Bluesky doesn't support scheduled posts via AT Protocol
    if (hasBluesky && scheduleTime) {
      return {
        error:
          "Bluesky does not support scheduled posts. Please post immediately or remove Bluesky from selected platforms.",
        data: null,
      };
    }

    // Get team owner's credentials
    const { data: team, error: teamError } = await supabaseAdminClient
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (teamError || !team) {
      throw new Error("Team not found");
    }

    const { data: ownerRole, error: ownerRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select(
        "postiz_email, postiz_password, bluesky_service, bluesky_identifier, bluesky_password"
      )
      .eq("user_id", team.owner_id)
      .single();

    // Handle case where team owner doesn't have a user_roles record yet
    if (ownerRoleError) {
      // PGRST116 = No rows found - team owner hasn't completed setup
      if (ownerRoleError.code === "PGRST116") {
        return {
          error: "Team owner has not set up social media accounts",
          data: null,
        };
      }
      // Real database error - throw it
      throw new Error(`Failed to fetch team owner credentials: ${ownerRoleError.message}`);
    }

    if (!ownerRole) {
      return {
        error: "Team owner has not set up social media accounts",
        data: null,
      };
    }

    // Separate Bluesky from other platforms
    const nonBlueskyPlatforms: string[] = [];
    const nonBlueskyIntegrationIds: string[] = [];

    for (let i = 0; i < platforms.length; i++) {
      if (platforms[i] !== "bluesky") {
        nonBlueskyPlatforms.push(platforms[i]);
        nonBlueskyIntegrationIds.push(integrationIds[i]);
      }
    }

    // Results will combine responses from both Bluesky and Postiz
    const allPostResults: Array<{ postId: string; integration: string }> = [];

    // Handle Bluesky posting directly (if included)
    if (hasBluesky) {
      if (
        !ownerRole.bluesky_service ||
        !ownerRole.bluesky_identifier ||
        !ownerRole.bluesky_password
      ) {
        return {
          error:
            "Team owner has not connected a Bluesky account. Please ask the team owner to connect Bluesky in their settings.",
          data: null,
        };
      }

      console.log("[Bluesky] Posting directly to Bluesky with video upload for team");

      const videoUrl = mediaUrls[0]; // Use first video URL
      const blueskyResult = await createBlueskyPostWithVideo(
        ownerRole.bluesky_service,
        ownerRole.bluesky_identifier,
        ownerRole.bluesky_password,
        message,
        videoUrl
      );

      if (blueskyResult.error) {
        return {
          error: blueskyResult.error,
          data: null,
        };
      }

      // Add Bluesky result to combined results
      allPostResults.push({
        postId: blueskyResult.data || "",
        integration: integrationIds[blueskyIndex],
      });

      console.log("[Bluesky] Team post created successfully:", blueskyResult.data);
    }

    // Handle non-Bluesky platforms via Postiz (if any)
    if (nonBlueskyPlatforms.length > 0) {
      if (!ownerRole.postiz_email || !ownerRole.postiz_password) {
        return {
          error: "Team owner has not set up Postiz account for social media posting.",
          data: null,
        };
      }

      // Create post using team owner's credentials
      const postResponse = await createPostizPost(
        ownerRole.postiz_email,
        ownerRole.postiz_password,
        nonBlueskyIntegrationIds,
        nonBlueskyPlatforms,
        message,
        mediaUrls,
        scheduleTime
      );

      if (postResponse.error) {
        throw new Error(postResponse.error);
      }

      // Add Postiz results to combined results
      if (postResponse.data) {
        allPostResults.push(...postResponse.data);
      }
    }

    // Save post IDs to database (same logic as personal posting)
    if (allPostResults.length > 0) {
      // Map integration IDs to platform identifiers
      const integrationToPlatform = new Map(
        integrationIds.map((id, index) => [id, platforms[index]])
      );

      // Group post IDs by platform
      const postIdsByPlatform: Record<string, string[]> = {};

      for (const post of allPostResults) {
        const platformIdentifier = integrationToPlatform.get(post.integration);
        if (platformIdentifier) {
          const columnName = getPlatformColumnName(platformIdentifier);
          if (!postIdsByPlatform[columnName]) {
            postIdsByPlatform[columnName] = [];
          }
          postIdsByPlatform[columnName].push(post.postId);
        }
      }

      // Get current clip data to append to existing arrays
      const { data: currentClip } = await supabaseAdminClient
        .from("user_clips")
        .select("*")
        .eq("id", clipId)
        .single();

      if (currentClip) {
        // Build update object - append new post IDs to existing arrays
        const updates: Record<string, string[]> = {};

        for (const [columnName, newPostIds] of Object.entries(postIdsByPlatform)) {
          const existingPostIds =
            ((currentClip as Record<string, unknown>)[columnName] as string[] | null) || [];
          updates[columnName] = [...existingPostIds, ...newPostIds];
        }

        // Update user_clips with new post IDs
        const { error: updateError } = await supabaseAdminClient
          .from("user_clips")
          .update(updates)
          .eq("id", clipId);

        if (updateError) {
          console.error("Failed to save team post IDs to database:", updateError);
          // Don't fail the operation - post was created successfully
        }
      }
    }

    // Track video_shared or video_scheduled events in PostHog
    if (allPostResults.length > 0) {
      try {
        // Get MP context for the team (uses team owner's MP info)
        const mpContext = await getMPTrackingContext(user.id, teamId);

        // Map integration IDs to platform identifiers for tracking
        const integrationToPlatform = new Map(
          integrationIds.map((id, index) => [id, platforms[index]])
        );

        // Track each platform share separately
        for (const post of allPostResults) {
          const platformIdentifier = integrationToPlatform.get(post.integration);
          const eventName = scheduleTime ? "video_scheduled" : "video_shared";

          await captureServerEvent(user.id, eventName, {
            // Share details
            user_clip_id: clipId,
            platform: platformIdentifier,
            platform_post_id: post.postId,
            message_length: message.length,
            // Schedule info (only for video_scheduled)
            ...(scheduleTime && { scheduled_time: scheduleTime }),
            // MP Context (will have team owner's MP info)
            ...mpContext,
          });
        }
      } catch (trackingError) {
        // Log but don't fail the request - analytics should never break core functionality
        console.error("PostHog team video share event capture failed:", trackingError);
      }
    }

    return {
      error: null,
      data: allPostResults,
    };
  } catch (error) {
    console.error("Error creating team social media post:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Get next available time slot for team owner's platform
 * @param teamId - Team ID
 * @param integrationId - Integration ID to get next slot for
 * @returns Next available slot datetime (ISO 8601) or error
 */
export async function getTeamOwnerNextAvailableSlotAction(
  teamId: string,
  integrationId: string
) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Verify user is a team member
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId,
    });

    if (!userRole) {
      return {
        error: "You are not a member of this team",
        data: null,
      };
    }

    // Get team owner's credentials
    const { data: team, error: teamError } = await supabaseAdminClient
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (teamError || !team) {
      throw new Error("Team not found");
    }

    const { data: ownerRole, error: ownerRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_password")
      .eq("user_id", team.owner_id)
      .single();

    // Handle case where team owner doesn't have a user_roles record yet
    if (ownerRoleError) {
      // PGRST116 = No rows found - team owner hasn't completed setup
      if (ownerRoleError.code === "PGRST116") {
        return {
          error: "Team owner has not set up Postiz account",
          data: null,
        };
      }
      // Real database error - throw it
      throw new Error(`Failed to fetch team owner credentials: ${ownerRoleError.message}`);
    }

    if (!ownerRole || !ownerRole.postiz_email || !ownerRole.postiz_password) {
      return {
        error: "Team owner has not set up Postiz account",
        data: null,
      };
    }

    // Get next slot using team owner's credentials
    const response = await getNextAvailableSlot(
      ownerRole.postiz_email,
      ownerRole.postiz_password,
      integrationId
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return {
      error: null,
      data: response.data,
    };
  } catch (error) {
    console.error("Error getting team owner next slot:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}
