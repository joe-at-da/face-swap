import { NextRequest, NextResponse } from "next/server";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { generateAndFormatEmbedding } from "@/services/ai/embedding-service";
import { handleError } from "@/lib/getErrorMessage";

const DEFAULT_BATCH_SIZE = 50;

/**
 * Admin-only endpoint to re-embed clips with the current embedding model.
 * Processes clips in batches. Call repeatedly with increasing offset until
 * `remaining` is 0.
 *
 * POST /api/admin/re-embed-clips
 * Body: { batchSize?: number, offset?: number, adminKey: string }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      batchSize = DEFAULT_BATCH_SIZE,
      offset = 0,
      adminKey,
    } = body;

    // Simple auth: require SUPABASE_SERVICE_KEY match
    if (!adminKey || adminKey !== process.env.SUPABASE_SERVICE_KEY) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Count total clips needing re-embedding
    const { count: totalCount } = await supabaseAdminClient
      .from("parliament_member_clips")
      .select("id", { count: "exact", head: true })
      .eq("is_deleted", false)
      .not("transcript", "is", null)
      .neq("transcript", "");

    // Fetch batch of clips
    const { data: clips, error: fetchError } = await supabaseAdminClient
      .from("parliament_member_clips")
      .select("id, transcript, description")
      .eq("is_deleted", false)
      .not("transcript", "is", null)
      .neq("transcript", "")
      .order("id")
      .range(offset, offset + batchSize - 1);

    if (fetchError) {
      return NextResponse.json(
        { error: `Fetch failed: ${fetchError.message}` },
        { status: 500 }
      );
    }

    if (!clips || clips.length === 0) {
      return NextResponse.json({
        success: true,
        processed: 0,
        remaining: 0,
        total: totalCount || 0,
        message: "No more clips to process",
      });
    }

    let successCount = 0;
    let errorCount = 0;
    const errors: string[] = [];

    // Process clips sequentially to respect API rate limits
    for (const clip of clips) {
      try {
        const updates: Record<string, string | null> = {};

        // Re-embed transcript
        if (clip.transcript) {
          const result = await generateAndFormatEmbedding(clip.transcript);
          if (result.data) {
            updates.transcript_embedding = result.data;
          }
        }

        // Re-embed description
        if (clip.description) {
          const result = await generateAndFormatEmbedding(clip.description);
          if (result.data) {
            updates.description_embedding = result.data;
          }
        }

        if (Object.keys(updates).length > 0) {
          const { error: updateError } = await supabaseAdminClient
            .from("parliament_member_clips")
            .update(updates)
            .eq("id", clip.id);

          if (updateError) {
            errors.push(`${clip.id}: update failed - ${updateError.message}`);
            errorCount++;
          } else {
            successCount++;
          }
        }
      } catch (err) {
        errors.push(`${clip.id}: ${err instanceof Error ? err.message : "Unknown error"}`);
        errorCount++;
      }
    }

    const remaining = Math.max(0, (totalCount || 0) - offset - clips.length);

    return NextResponse.json({
      success: true,
      processed: successCount,
      errors: errorCount,
      errorDetails: errors.length > 0 ? errors : undefined,
      remaining,
      nextOffset: offset + clips.length,
      total: totalCount || 0,
    });
  } catch (error) {
    const message = handleError(error, {
      component: "api",
      action: "POST /api/admin/re-embed-clips",
      feature: "re-embedding",
    });
    return NextResponse.json(
      { error: message || "Internal server error" },
      { status: 500 }
    );
  }
}
