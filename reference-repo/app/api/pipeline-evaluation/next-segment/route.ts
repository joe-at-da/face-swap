import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import {
  EVALUATION_PROCESSING_RUN_IDS,
  LOCK_TIMEOUT_MINUTES,
} from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";
import type { EvaluableSegment } from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";

export async function GET() {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Check if user has @veedoo.io or @veedoo.com email
    const email = user.email;
    if (
      !email ||
      (!email.endsWith("@veedoo.io") && !email.endsWith("@veedoo.com"))
    ) {
      return NextResponse.json(
        { error: "Forbidden: Access restricted to Veedoo team members" },
        { status: 403 }
      );
    }

    // Check if we have processing run IDs configured
    if (EVALUATION_PROCESSING_RUN_IDS.length === 0) {
      return NextResponse.json({
        success: true,
        complete: true,
        message: "No processing runs configured for evaluation",
      });
    }

    const lockExpiry = new Date(
      Date.now() - LOCK_TIMEOUT_MINUTES * 60 * 1000
    ).toISOString();

    // First, get total count of evaluable segments to know when we've checked all
    const { count: totalEvaluableSegments } = await supabaseAdminClient
      .from("event_processing_segments")
      .select("id", { count: "exact", head: true })
      .in("processing_run_id", EVALUATION_PROCESSING_RUN_IDS)
      .not("member_id", "is", null)
      .is("manually_assigned_member_id", null)
      .gt("duration_seconds", 5);

    // Fetch segments in batches until we find an available one
    // This avoids URL length issues from large NOT IN clauses (when thousands are evaluated)
    // 1. Must be in configured processing runs
    // 2. Must have auto-detected member_id
    // 3. Must NOT have manually_assigned_member_id
    // 4. Must NOT have a completed evaluation
    // 5. Must be unlocked OR locked by current user OR have expired lock - checked at DB level
    const BATCH_SIZE = 50;
    const MAX_SEGMENTS_TO_CHECK = totalEvaluableSegments ?? 10000; // Safety limit
    let segments = null;
    let batchOffset = 0;
    let segmentsChecked = 0;

    while (segmentsChecked < MAX_SEGMENTS_TO_CHECK) {
      const { data: batchSegments, error: segmentsError } =
        await supabaseAdminClient
          .from("event_processing_segments")
          .select(
            "id, processing_run_id, clip_url, thumbnail_url, member_id, transcript, start_seconds"
          )
          .in("processing_run_id", EVALUATION_PROCESSING_RUN_IDS)
          .not("member_id", "is", null)
          .is("manually_assigned_member_id", null)
          .gt("duration_seconds", 5)
          .order("created_at", { ascending: true })
          .range(batchOffset, batchOffset + BATCH_SIZE - 1);

      if (segmentsError) {
        console.error("Error fetching segments:", segmentsError);
        return NextResponse.json(
          { error: "Failed to fetch segments" },
          { status: 500 }
        );
      }

      if (!batchSegments || batchSegments.length === 0) {
        // No more segments available in database
        break;
      }

      segments = batchSegments;
      segmentsChecked += batchSegments.length;
      batchOffset += BATCH_SIZE;

      // Check if any segments in this batch are available
      // Fetch evaluations and filter based on completion AND lock status
      const segmentIds = segments.map((s) => s.id);
      const { data: batchEvaluations } = await supabaseAdminClient
        .from("segment_evaluations")
        .select("segment_id, is_correct, locked_by, locked_at")
        .in("segment_id", segmentIds);

      // Build map of segment evaluations
      const evalMap = new Map(
        batchEvaluations?.map((e) => [e.segment_id, e]) ?? []
      );

      // Filter segments to only include available ones:
      // 1. No evaluation record at all (never evaluated or locked), OR
      // 2. Evaluation exists but is_correct is NULL AND (no lock OR locked by current user OR expired lock)
      segments = segments.filter((s) => {
        const evaluation = evalMap.get(s.id);

        // Skip if already evaluated (is_correct is not null)
        if (evaluation && evaluation.is_correct !== null) {
          return false;
        }

        // No evaluation record = available
        if (!evaluation) {
          return true;
        }

        // Has evaluation but not completed (is_correct is null)
        // Check lock status: no lock, or locked by current user, or expired lock
        if (!evaluation.locked_by || evaluation.locked_by === user.id) {
          return true;
        }

        // Locked by another user - check if expired
        if (evaluation.locked_at) {
          const lockTime = new Date(evaluation.locked_at);
          const expiryTime = new Date(lockExpiry);
          return lockTime <= expiryTime; // Return true if lock expired
        }

        // Locked but no locked_at timestamp - should not happen, but treat as locked
        return false;
      });

      if (segments.length > 0) {
        // Found some available segments in this batch
        break;
      }
      // All segments in this batch were unavailable, try next batch
    }

    if (!segments || segments.length === 0) {
      return NextResponse.json({
        success: true,
        complete: true,
        message: "No segments available for evaluation",
      });
    }

    // Since we already filtered for available segments in the batch loop,
    // we can simply take the first one (oldest by created_at)
    const selectedSegment = segments[0];

    // Lock the segment atomically - must not overwrite completed evaluations
    // First, try to update existing record (only if is_correct IS NULL - not yet evaluated)
    const { data: updateResult, error: updateError } = await supabaseAdminClient
      .from("segment_evaluations")
      .update({
        locked_by: user.id,
        locked_at: new Date().toISOString(),
      })
      .eq("segment_id", selectedSegment.id)
      .is("is_correct", null) // Only update if not yet evaluated
      .select();

    // If update failed with an error, return immediately
    if (updateError) {
      console.error("Error locking segment:", updateError);
      return NextResponse.json(
        { error: "Failed to lock segment, please try again" },
        { status: 500 }
      );
    }

    // If no rows updated (doesn't exist or already evaluated), try insert
    if (!updateResult || updateResult.length === 0) {
      const { error: insertError } = await supabaseAdminClient
        .from("segment_evaluations")
        .insert({
          segment_id: selectedSegment.id,
          processing_run_id: selectedSegment.processing_run_id,
          evaluated_by: user.id,
          locked_by: user.id,
          locked_at: new Date().toISOString(),
          is_correct: null as unknown as boolean,
          error_reason: null,
        });

      // If insert failed, segment was likely evaluated by another user between queries
      if (insertError) {
        // Log the race condition occurrence
        console.warn(
          "Segment was evaluated by another user during lock attempt:",
          selectedSegment.id
        );
        // Fetch next segment instead
        return NextResponse.json(
          { error: "Segment was just evaluated, fetching next one" },
          { status: 409 } // Conflict
        );
      }
    }

    // Fetch speaker faces for this segment
    const { data: speakerFaces, error: facesError } = await supabaseAdminClient
      .from("segment_speaker_faces")
      .select("id, s3_url, face_index, quality_score")
      .eq("segment_id", selectedSegment.id)
      .order("face_index", { ascending: true })
      .limit(4);

    if (facesError) {
      console.error("Error fetching speaker faces:", facesError);
    }

    // Fetch MP data for the detected member
    const { data: member, error: memberError } = await supabaseAdminClient
      .from("parliament_members")
      .select("member_id, display_name, party_name, constituency_name")
      .eq("member_id", selectedSegment.member_id!)
      .single();

    if (memberError) {
      console.error("Error fetching member:", memberError);
    }

    // Fetch MP portraits for the detected member
    const { data: allPortraits, error: portraitsError } =
      await supabaseAdminClient
        .from("parliament_member_portraits")
        .select("id, image_url, crop_type, is_primary")
        .eq("member_id", selectedSegment.member_id!)
        .eq("is_deleted", false);

    if (portraitsError) {
      console.error("Error fetching MP portraits:", portraitsError);
    }

    // Fetch event URL from parliament_events via event_processing_runs
    const { data: processingRun, error: processingRunError } =
      await supabaseAdminClient
        .from("event_processing_runs")
        .select(
          `
          parliament_events (
            event_url,
            session_start_time
          )
        `
        )
        .eq("id", selectedSegment.processing_run_id)
        .single();

    if (processingRunError) {
      console.error("Error fetching processing run:", processingRunError);
    }

    const parliamentEvents = processingRun?.parliament_events as {
      event_url: string | null;
      session_start_time: string | null;
    } | null;
    const eventUrl = parliamentEvents?.event_url ?? null;
    const sessionStartTime = parliamentEvents?.session_start_time ?? null;

    // Sort portraits: parliament.uk first (preferred), then by is_primary, then by crop_type
    const sortedPortraits = (allPortraits ?? []).sort((a, b) => {
      const aIsParliament = a.image_url?.includes("parliament.uk") ?? false;
      const bIsParliament = b.image_url?.includes("parliament.uk") ?? false;

      // Parliament.uk URLs first (preferred source)
      if (aIsParliament !== bIsParliament) {
        return aIsParliament ? -1 : 1;
      }

      // Then by is_primary (true first)
      if (a.is_primary !== b.is_primary) {
        return a.is_primary ? -1 : 1;
      }

      // Then by crop_type
      return (a.crop_type ?? 0) - (b.crop_type ?? 0);
    });

    // Separate parliament and non-parliament portraits for fallback mechanism
    const parliamentPortraits = sortedPortraits.filter((p) =>
      p.image_url?.includes("parliament.uk")
    );
    const nonParliamentPortraits = sortedPortraits.filter(
      (p) => !p.image_url?.includes("parliament.uk")
    );

    // Take first 4 parliament portraits, with fallbacks from non-parliament
    const selectedPortraits = parliamentPortraits.slice(0, 4);

    // Transform URLs - proxy parliament.uk URLs, include fallback for each
    const transformedPortraits = selectedPortraits.map((p, index) => {
      const originalUrl = p.image_url ?? "";
      const imageUrl = originalUrl.includes("parliament.uk")
        ? `/api/proxy-image?url=${encodeURIComponent(originalUrl)}`
        : originalUrl;

      // Find a non-parliament fallback image (same crop type preferred)
      const fallback =
        nonParliamentPortraits.find((np) => np.crop_type === p.crop_type) ||
        nonParliamentPortraits[index] ||
        nonParliamentPortraits[0];

      return {
        id: p.id,
        imageUrl,
        fallbackUrl: fallback?.image_url ?? null,
        cropType: p.crop_type ?? 0,
        isPrimary: p.is_primary,
      };
    });

    const segment: EvaluableSegment = {
      segmentId: selectedSegment.id,
      clipUrl: selectedSegment.clip_url,
      thumbnailUrl: selectedSegment.thumbnail_url,
      memberId: selectedSegment.member_id!,
      memberName: member?.display_name ?? null,
      partyName: member?.party_name ?? null,
      constituencyName: member?.constituency_name ?? null,
      transcript: selectedSegment.transcript,
      speakerFaces:
        speakerFaces?.map((f) => ({
          id: f.id,
          s3Url: f.s3_url ?? "",
          faceIndex: f.face_index,
          qualityScore: f.quality_score,
        })) ?? [],
      mpPortraits: transformedPortraits,
      processingRunId: selectedSegment.processing_run_id,
      eventUrl,
      startSeconds: selectedSegment.start_seconds ?? null,
      sessionStartTime,
    };

    return NextResponse.json({
      success: true,
      complete: false,
      segment,
    });
  } catch (error) {
    console.error("Next segment error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch next segment: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
