import "server-only";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { captureServerEvent } from "@/lib/posthog-server";
import { ErrorLogger } from "@/lib/errorLogger";

/**
 * Increment the view count for a clip.
 * This is a server-only utility — NOT a server action, so it cannot be called from client code.
 *
 * TODO: Replace read-then-write with an atomic RPC call
 * (SET view_count = view_count + 1) to prevent lost updates under
 * concurrent page loads. Requires a Supabase migration to add the function.
 */
export async function incrementViewCount(clipId: string): Promise<void> {
  try {
    const { data: currentClip, error: fetchError } = await supabaseAdminClient
      .from("user_clips")
      .select("view_count, user_id")
      .eq("id", clipId)
      .single();

    if (fetchError || !currentClip) {
      ErrorLogger.logDatabaseError(fetchError, "incrementViewCount:fetch", "user_clips", clipId);
      return;
    }

    const { error: updateError } = await supabaseAdminClient
      .from("user_clips")
      .update({
        view_count: (currentClip.view_count || 0) + 1,
      })
      .eq("id", clipId);

    if (updateError) {
      ErrorLogger.logDatabaseError(updateError, "incrementViewCount:update", "user_clips", clipId);
    }

    try {
      const distinctId = currentClip.user_id || "anonymous";
      await captureServerEvent(distinctId, "clip_viewed", {
        clip_id: clipId,
        view_count: (currentClip.view_count || 0) + 1,
        source: "public_clip_page",
      });
    } catch (trackingError) {
      ErrorLogger.logError(trackingError instanceof Error ? trackingError : new Error(String(trackingError)), { action: "incrementViewCount:posthog", feature: "clips", additionalContext: { clipId } });
    }
  } catch (error) {
    ErrorLogger.logError(error instanceof Error ? error : new Error(String(error)), { action: "incrementViewCount", feature: "clips", additionalContext: { clipId } });
  }
}
