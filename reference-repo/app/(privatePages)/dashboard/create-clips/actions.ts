"use server";
import "server-only";

import { getErrorMessage } from "@/lib/getErrorMessage";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { getUserFollowedMemebers } from "@/app/actions/user";
import {
  isLiberalDemocratCached,
  getLDMemberIds,
} from "@/lib/liberal-democrat-helpers";
import { captureServerEvent } from "@/lib/posthog-server";
import { ErrorLogger } from "@/lib/errorLogger";

// TODO: Implement this function
export async function markClipAsFalsePositive(
  _clip_id: string,
  teamId?: string
) {
  try {
    const { data: clip, error: clipError } = await supabaseAdminClient
      .from("parliament_member_clips")
      .select("*")
      .eq("id", _clip_id)
      .single();
    if (clipError) {
      throw new Error("Error getting clip: " + clipError.message);
    }
    if (!clip) {
      throw new Error("Clip not found");
    }

    const memeberId = clip.member_id;
    const supabaseServerClient = await createSupabaseServerClient();

    const {
      data: { user },
      error: userError,
    } = await supabaseServerClient.auth.getUser();
    if (userError) {
      throw new Error("Error getting user: " + userError.message);
    }
    if (!user) {
      throw new Error("User not found");
    }

    const userId = user.id;

    const { data: followedMps, error: followedMpsError } =
      await getUserFollowedMemebers(userId);
    if (followedMpsError) {
      throw new Error("Error getting followed MPs: " + followedMpsError);
    }

    const isFollowedMp = followedMps && followedMps.includes(memeberId);

    if (!isFollowedMp) {
      // IDOR protection: verify team membership when teamId is provided
      if (teamId) {
        const { data: isMember, error: memberError } =
          await supabaseAdminClient.rpc("is_team_member", {
            p_team_id: teamId,
            p_user_id: userId,
          });

        if (memberError || !isMember) {
          throw new Error("User is not a member of this team");
        }
      }

      // Fallback: allow LD users to mark other LD MPs' clips as incorrect
      const isLD = await isLiberalDemocratCached(
        userId,
        teamId,
        supabaseAdminClient
      );
      if (!isLD) {
        throw new Error("User does not follow this MP");
      }

      const ldMemberIds = await getLDMemberIds(supabaseAdminClient);
      if (!ldMemberIds.includes(memeberId)) {
        throw new Error("User does not follow this MP");
      }

      // Audit: PostHog for analytics, ErrorLogger for operational visibility
      captureServerEvent(userId, "ld_cross_clip_deletion", {
        clip_id: _clip_id,
        member_id: memeberId,
      }).catch(() => {}); // non-critical

      ErrorLogger.logEvent("Cross-LD clip deletion", {
        userId,
        component: "clips",
        action: "markClipAsFalsePositive",
        feature: "ld-clips",
        additionalContext: { clip_id: _clip_id, member_id: memeberId },
      });
    }

    const { error: clipUpdateError } = await supabaseAdminClient
      .from("parliament_member_clips")
      .update({
        is_false_positive: true,
        is_deleted: true,
        deleted_at: new Date().toISOString(),
      })
      .eq("id", _clip_id);

    if (clipUpdateError) {
      throw new Error(
        "Error marking clip as false positive: " + clipUpdateError.message
      );
    }

    return {
      data: true,
      error: null,
    };
  } catch (error: unknown) {
    const message = getErrorMessage(error);
    console.error("error in markClipAsFalsePositive: ", message);
    return {
      error: message,
      data: null,
    };
  }
}
