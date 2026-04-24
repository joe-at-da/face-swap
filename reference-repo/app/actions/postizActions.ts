"use server";

import {
  getConnectSocialMediaAccounts,
  signupUserToPostiz,
  disconnectSocialMediaIntegration,
  createPostizPost,
  getNextAvailableSlot,
} from "@/services/postiz/postizApi";
import {
  createBlueskyPostWithVideo,
  validateBlueskyCredentials,
  getBlueskyProfile,
} from "@/services/bluesky/blueskyApi";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { captureServerEvent } from "@/lib/posthog-server";
import { getMPTrackingContext } from "@/lib/posthog-helpers";
import { isFacebookAllowed } from "@/lib/facebookAllowlist";

/**
 * Map platform identifier to database column name
 * @param identifier - Platform identifier (e.g., 'x', 'linkedin', 'facebook')
 * @returns Database column name (e.g., 'twitter_post_ids', 'linkedin_post_ids')
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

export async function getUserConnectSocialMediaAccountsActions() {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("*")
      .eq("user_id", user.id)
      .single();
    if (userRoleError) {
      throw new Error("Failed to fetch user role");
    }

    if (!userRole) {
      throw new Error("User role not found");
    }

    const postizEmail = userRole.postiz_email;

    // Get Postiz platforms (if Postiz account exists)
    let platforms: Array<{
      name: string;
      identifier: string;
      isConnected: boolean;
      integrationId?: string;
      profile?: string;
      profileName?: string;
      picture?: string;
    }> = [];

    if (postizEmail) {
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
    }

    // Check if Bluesky credentials exist in Supabase (stored separately from Postiz)
    // Use cached profile data (avatar, display_name) to avoid API calls on every poll
    if (
      userRole.bluesky_service &&
      userRole.bluesky_identifier &&
      userRole.bluesky_password
    ) {
      platforms.push({
        name: "Bluesky",
        identifier: "bluesky",
        isConnected: true,
        integrationId: "bluesky-direct", // Synthetic ID for direct AT Protocol posting
        profile: userRole.bluesky_identifier,
        profileName: userRole.bluesky_display_name || userRole.bluesky_identifier,
        picture: userRole.bluesky_avatar || undefined,
      });
    }

    return {
      error: null,
      data: platforms,
      postizNotSetup: !postizEmail,
    };
  } catch (error) {
    console.error("Error getting user connect social media accounts:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Create Postiz account for the current user
 * @returns Success/error response
 */
export async function createPostizAccountAction() {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Check if Postiz account already exists
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_api_key")
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      throw new Error("Failed to fetch user role");
    }

    // If Postiz account already exists, return success
    if (userRole && userRole.postiz_email && userRole.postiz_api_key) {
      return {
        error: null,
        data: "Postiz account already exists",
        alreadyExists: true,
      };
    }

    // Create Postiz account
    const email = user.id + "@mpai.com";
    const password = user.id;
    const company = user.email || user.id;

    const response = await signupUserToPostiz(email, password, company);

    if (response.error) {
      throw new Error(response.error);
    }

    const apiKey = response.data;
    if (!apiKey) {
      throw new Error("Failed to create Postiz account - no API key returned");
    }

    // Update user_roles with Postiz credentials
    const { error: updateError } = await supabaseAdminClient
      .from("user_roles")
      .update({
        postiz_api_key: apiKey,
        postiz_email: email,
        postiz_password: password,
      })
      .eq("user_id", user.id);

    if (updateError) {
      throw new Error(
        `Failed to save Postiz credentials: ${updateError.message}`
      );
    }

    return {
      error: null,
      data: "Postiz account created successfully",
      alreadyExists: false,
    };
  } catch (error) {
    console.error("Error creating Postiz account:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Get OAuth URL for connecting a social media platform
 * Returns our proxy URL that handles Postiz authentication before OAuth
 * @param platform - Platform identifier (e.g., 'x', 'linkedin', 'facebook')
 * @returns OAuth proxy URL or error
 */
export async function connectSocialMediaPlatformAction(platform: string) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Check if Postiz account exists
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_password")
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      throw new Error("Failed to fetch user role");
    }

    if (!userRole || !userRole.postiz_email || !userRole.postiz_password) {
      return {
        error: "Please complete setup first to connect social media accounts",
        data: null,
      };
    }

    // Return our OAuth proxy URL instead of Postiz OAuth URL
    // This route will handle logging into Postiz before starting OAuth
    const proxyUrl = `/api/oauth/start?platform=${platform}`;

    return {
      error: null,
      data: proxyUrl,
    };
  } catch (error) {
    console.error("Error getting OAuth URL:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Disconnect a social media platform
 * @param integrationId - Integration ID to disconnect
 * @returns Success or error
 */
export async function disconnectSocialMediaPlatformAction(
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

    // Get Postiz credentials
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_password")
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      throw new Error("Failed to fetch user role");
    }

    if (!userRole || !userRole.postiz_email || !userRole.postiz_password) {
      return {
        error: "Postiz account not found",
        data: null,
      };
    }

    // Disconnect via Postiz API
    const response = await disconnectSocialMediaIntegration(
      userRole.postiz_email,
      userRole.postiz_password,
      integrationId
    );

    if (response.error) {
      throw new Error(response.error);
    }

    // Track social account disconnection
    try {
      await captureServerEvent(user.id, "social_account_disconnected", {
        integration_id: integrationId,
        platform: "postiz_integration", // Platform can be derived from integration lookup if needed
      });
    } catch (trackingError) {
      console.error("PostHog social_account_disconnected event capture failed:", trackingError);
    }

    return {
      error: null,
      data: true,
    };
  } catch (error) {
    console.error("Error disconnecting platform:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Get next available time slot for scheduling a post on a platform
 * @param integrationId - Integration ID to get next slot for
 * @returns Next available slot datetime (ISO 8601) or error
 */
export async function getNextAvailableSlotAction(integrationId: string) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Get Postiz credentials
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_password")
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      throw new Error("Failed to fetch user role");
    }

    if (!userRole || !userRole.postiz_email || !userRole.postiz_password) {
      return {
        error: "Postiz account not found. Please complete setup first.",
        data: null,
      };
    }

    // Fetch next available slot from Postiz
    const response = await getNextAvailableSlot(
      userRole.postiz_email,
      userRole.postiz_password,
      integrationId
    );

    return response;
  } catch (error) {
    console.error("Error getting next available slot:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Create a social media post and save post IDs to database
 * @param userClipId - User clip ID to save post IDs to
 * @param integrationIds - Array of integration IDs to post to
 * @param platformIdentifiers - Array of platform identifiers (e.g., ['x', 'linkedin'])
 * @param message - Post content/message
 * @param mediaUrls - Array of media URLs (video/image) - Postiz will download from these URLs
 * @param scheduleTime - Optional ISO 8601 datetime for scheduling
 * @returns Post ID array on success or error
 */
export async function createSocialMediaPostAction(
  userClipId: string,
  integrationIds: string[],
  platformIdentifiers: string[],
  message: string,
  mediaUrls: string[],
  scheduleTime?: string | null
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

    // Check if Bluesky is included in platforms
    const blueskyIndex = platformIdentifiers.indexOf("bluesky");
    const hasBluesky = blueskyIndex !== -1;

    // Bluesky doesn't support scheduled posts via AT Protocol
    if (hasBluesky && scheduleTime) {
      // Track share failure - Bluesky scheduled not supported
      try {
        await captureServerEvent(user.id, "share_failed", {
          user_clip_id: userClipId,
          platform: "bluesky",
          error_type: "bluesky_scheduled_not_supported",
          error_message: "Bluesky does not support scheduled posts",
        });
      } catch (trackingError) {
        console.error("PostHog share_failed event capture failed:", trackingError);
      }
      return {
        error:
          "Bluesky does not support scheduled posts. Please post immediately or remove Bluesky from selected platforms.",
        data: null,
      };
    }

    // Get user credentials (Postiz + Bluesky)
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select(
        "postiz_email, postiz_password, bluesky_service, bluesky_identifier, bluesky_password"
      )
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      throw new Error("Failed to fetch user role");
    }

    // Separate Bluesky from other platforms
    const nonBlueskyPlatforms: string[] = [];
    const nonBlueskyIntegrationIds: string[] = [];

    for (let i = 0; i < platformIdentifiers.length; i++) {
      if (platformIdentifiers[i] !== "bluesky") {
        nonBlueskyPlatforms.push(platformIdentifiers[i]);
        nonBlueskyIntegrationIds.push(integrationIds[i]);
      }
    }

    // Results will combine responses from both Bluesky and Postiz
    const allPostResults: Array<{ postId: string; integration: string }> = [];

    // Handle Bluesky posting directly (if included)
    if (hasBluesky) {
      if (
        !userRole?.bluesky_service ||
        !userRole?.bluesky_identifier ||
        !userRole?.bluesky_password
      ) {
        // Track share failure - Bluesky credentials missing
        try {
          await captureServerEvent(user.id, "share_failed", {
            user_clip_id: userClipId,
            platform: "bluesky",
            error_type: "bluesky_credentials_missing",
            error_message: "Bluesky credentials not found",
          });
        } catch (trackingError) {
          console.error("PostHog share_failed event capture failed:", trackingError);
        }
        return {
          error:
            "Bluesky credentials not found. Please connect your Bluesky account first.",
          data: null,
        };
      }

      console.log("[Bluesky] Posting directly to Bluesky with video upload");

      const videoUrl = mediaUrls[0]; // Use first video URL
      const blueskyResult = await createBlueskyPostWithVideo(
        userRole.bluesky_service,
        userRole.bluesky_identifier,
        userRole.bluesky_password,
        message,
        videoUrl
      );

      if (blueskyResult.error) {
        // Track share failure - Bluesky posting error
        try {
          await captureServerEvent(user.id, "share_failed", {
            user_clip_id: userClipId,
            platform: "bluesky",
            error_type: "bluesky_post_error",
            error_message: blueskyResult.error,
          });
        } catch (trackingError) {
          console.error("PostHog share_failed event capture failed:", trackingError);
        }
        return {
          error: blueskyResult.error,
          data: null,
        };
      }

      // Add Bluesky result to combined results
      // Use the post URI as postId and "bluesky" as integration identifier
      allPostResults.push({
        postId: blueskyResult.data || "",
        integration: integrationIds[blueskyIndex], // Use the original integration ID
      });

      console.log("[Bluesky] Post created successfully:", blueskyResult.data);
    }

    // Handle non-Bluesky platforms via Postiz (if any)
    if (nonBlueskyPlatforms.length > 0) {
      if (!userRole?.postiz_email || !userRole?.postiz_password) {
        // Track share failure - Postiz not setup
        try {
          await captureServerEvent(user.id, "share_failed", {
            user_clip_id: userClipId,
            platforms: nonBlueskyPlatforms,
            error_type: "postiz_not_setup",
            error_message: "Postiz account not found",
          });
        } catch (trackingError) {
          console.error("PostHog share_failed event capture failed:", trackingError);
        }
        return {
          error: "Postiz account not found. Please complete setup first.",
          data: null,
        };
      }

      console.log("Creating post with video URLs for Postiz:", mediaUrls);

      // Create post via Postiz API
      const response = await createPostizPost(
        userRole.postiz_email,
        userRole.postiz_password,
        nonBlueskyIntegrationIds,
        nonBlueskyPlatforms,
        message,
        mediaUrls,
        scheduleTime
      );

      if (response.error) {
        // Track share failure - Postiz API error
        try {
          await captureServerEvent(user.id, "share_failed", {
            user_clip_id: userClipId,
            platforms: nonBlueskyPlatforms,
            error_type: "postiz_api_error",
            error_message: response.error,
          });
        } catch (trackingError) {
          console.error("PostHog share_failed event capture failed:", trackingError);
        }
        throw new Error(response.error);
      }

      // Validate that posts were actually created
      if (!response.data || response.data.length === 0) {
        throw new Error("No posts were created. Please check your social media connection.");
      }

      // Add Postiz results to combined results
      allPostResults.push(...response.data);
    }

    // Use combined results for database updates
    const response = { data: allPostResults, error: null };

    // Save post IDs to database
    // Response.data is an array of {postId, integration} objects
    if (response.data && response.data.length > 0) {
      // Map integration IDs to platform identifiers
      const integrationToPlatform = new Map(
        integrationIds.map((id, index) => [id, platformIdentifiers[index]])
      );

      // Group post IDs by platform
      const postIdsByPlatform: Record<string, string[]> = {};

      for (const post of response.data) {
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
        .eq("id", userClipId)
        .single();

      if (currentClip) {
        // Build update object - append new post IDs to existing arrays
        const updates: Record<string, string[]> = {};

        for (const [columnName, newPostIds] of Object.entries(
          postIdsByPlatform
        )) {
          // Get existing post IDs from the current clip
          const existingPostIds =
            ((currentClip as Record<string, unknown>)[columnName] as
              | string[]
              | null) || [];
          // Append new post IDs
          updates[columnName] = [...existingPostIds, ...newPostIds];
        }

        // Update user_clips with new post IDs
        const { error: updateError } = await supabaseAdminClient
          .from("user_clips")
          .update(updates)
          .eq("id", userClipId);

        if (updateError) {
          console.error("Failed to save post IDs to database:", updateError);
          // Don't fail the entire operation, just log the error
          // The post was still created successfully on social media
        }
      }

      // Track video_shared or video_scheduled events in PostHog
      try {
        // Get team_id from the clip to determine MP context
        const { data: clipData } = await supabaseAdminClient
          .from("user_clips")
          .select("team_id")
          .eq("id", userClipId)
          .single();

        const mpContext = await getMPTrackingContext(user.id, clipData?.team_id);

        // Map integration IDs to platform identifiers for tracking
        const integrationToPlatform = new Map(
          integrationIds.map((id, index) => [id, platformIdentifiers[index]])
        );

        // Track each platform share separately
        for (const post of response.data) {
          const platformIdentifier = integrationToPlatform.get(post.integration);
          const eventName = scheduleTime ? "video_scheduled" : "video_shared";

          await captureServerEvent(user.id, eventName, {
            // Share details
            user_clip_id: userClipId,
            platform: platformIdentifier,
            platform_post_id: post.postId,
            message_length: message.length,
            // Schedule info (only for video_scheduled)
            ...(scheduleTime && { scheduled_time: scheduleTime }),
            // MP Context
            ...mpContext,
          });
        }
      } catch (trackingError) {
        // Log but don't fail the request - analytics should never break core functionality
        console.error("PostHog video share event capture failed:", trackingError);
      }
    }

    return {
      error: null,
      data: response.data,
    };
  } catch (error) {
    console.error("Error creating social media post:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Connect Bluesky account and store credentials
 * Posts directly to Bluesky using AT Protocol (not via Postiz)
 * @param service - Bluesky service URL (e.g., https://bsky.social)
 * @param identifier - Bluesky account identifier/handle
 * @param password - Bluesky app password
 * @returns Success or error
 */
export async function connectBlueskyAccountAction(
  service: string,
  identifier: string,
  password: string
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

    // Validate credentials by attempting to login to Bluesky directly
    const validationResult = await validateBlueskyCredentials(
      service,
      identifier,
      password
    );

    if (validationResult.error || !validationResult.data) {
      return {
        error: `Invalid Bluesky credentials: ${validationResult.error}`,
        data: null,
      };
    }

    // Fetch profile data to cache avatar and display name
    const profileResult = await getBlueskyProfile(service, identifier, password);

    // Store Bluesky credentials and cached profile data in user_roles
    const { error: updateError } = await supabaseAdminClient
      .from("user_roles")
      .update({
        bluesky_service: service,
        bluesky_identifier: identifier,
        bluesky_password: password,
        bluesky_avatar: profileResult.data?.avatar || null,
        bluesky_display_name: profileResult.data?.displayName || null,
      })
      .eq("user_id", user.id);

    if (updateError) {
      throw new Error(`Failed to store Bluesky credentials: ${updateError.message}`);
    }

    // Track Bluesky account connection
    try {
      await captureServerEvent(user.id, "social_account_connected", {
        platform: "bluesky",
        identifier: identifier,
        has_profile_cached: !!profileResult.data?.avatar,
      });
    } catch (trackingError) {
      console.error("PostHog social_account_connected event capture failed:", trackingError);
    }

    return {
      error: null,
      data: "Bluesky account connected successfully",
    };
  } catch (error) {
    console.error("[Bluesky] Error connecting account:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Check if user has Bluesky credentials stored
 * @returns Bluesky credentials if they exist, null otherwise
 */
export async function getBlueskyCredentialsAction() {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("bluesky_service, bluesky_identifier, bluesky_password")
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      throw new Error("Failed to fetch user role");
    }

    if (
      !userRole ||
      !userRole.bluesky_service ||
      !userRole.bluesky_identifier ||
      !userRole.bluesky_password
    ) {
      return {
        error: null,
        data: null, // No credentials stored
      };
    }

    return {
      error: null,
      data: {
        service: userRole.bluesky_service,
        identifier: userRole.bluesky_identifier,
        hasPassword: !!userRole.bluesky_password,
      },
    };
  } catch (error) {
    console.error("Error getting Bluesky credentials:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}

/**
 * Returns platform identifiers that should show as "Coming Soon" for current user
 */
export async function getRestrictedPlatformsAction(): Promise<{
  error: string | null;
  data: string[];
}> {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    const restricted: string[] = [];
    if (!isFacebookAllowed(user.email ?? "")) {
      restricted.push("facebook");
    }

    return { error: null, data: restricted };
  } catch (error) {
    console.error("Error getting restricted platforms:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: ["facebook"],
    };
  }
}

/**
 * Disconnect Bluesky account (remove stored credentials)
 * @returns Success or error
 */
export async function disconnectBlueskyAccountAction() {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error("Authentication required");
    }

    // Remove Bluesky credentials and cached profile data from user_roles
    const { error: updateError } = await supabaseAdminClient
      .from("user_roles")
      .update({
        bluesky_service: null,
        bluesky_identifier: null,
        bluesky_password: null,
        bluesky_avatar: null,
        bluesky_display_name: null,
      })
      .eq("user_id", user.id);

    if (updateError) {
      throw new Error(
        `Failed to remove Bluesky credentials: ${updateError.message}`
      );
    }

    // Track Bluesky account disconnection
    try {
      await captureServerEvent(user.id, "social_account_disconnected", {
        platform: "bluesky",
      });
    } catch (trackingError) {
      console.error("PostHog social_account_disconnected event capture failed:", trackingError);
    }

    return {
      error: null,
      data: true,
    };
  } catch (error) {
    console.error("Error disconnecting Bluesky:", error);
    return {
      error: error instanceof Error ? error.message : String(error),
      data: null,
    };
  }
}
