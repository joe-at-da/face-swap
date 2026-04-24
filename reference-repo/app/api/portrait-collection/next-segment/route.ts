import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import {
  EVALUATION_PROCESSING_RUN_IDS,
  LOCK_TIMEOUT_MINUTES,
} from "@/app/(privatePages)/dashboard/portrait-collection/constants";
import type {
  UnidentifiedSegment,
  MPCandidate,
  SpeakerFace,
} from "@/app/(privatePages)/dashboard/portrait-collection/constants";

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
        message: "No processing runs configured for portrait collection",
      });
    }

    const lockExpiry = new Date(
      Date.now() - LOCK_TIMEOUT_MINUTES * 60 * 1000
    ).toISOString();

    // First, get total count of evaluable segments to know when we've checked all
    const { count: totalUnidentifiedSegments } = await supabaseAdminClient
      .from("event_processing_segments")
      .select("id", { count: "exact", head: true })
      .in("processing_run_id", EVALUATION_PROCESSING_RUN_IDS)
      .is("member_id", null) // Unidentified segments only (member_id IS NULL)
      .is("manually_assigned_member_id", null) // Not yet manually identified
      .gt("asd_num_faces_saved", 0);

    // Fetch segments for portrait collection in batches until we find an available one
    // Filters (using event_processing_segments as source of truth):
    // 1. Must be in configured processing runs
    // 2. Must be unidentified (is_unidentified = true OR member_id IS NULL)
    // 3. Must NOT have manually_assigned_member_id (this field is set when portrait collection completes)
    // 4. Must have faces detected (asd_num_faces_saved > 0)
    // Lock checking is done below using portrait_collection_evaluations
    const BATCH_SIZE = 50;
    const MAX_SEGMENTS_TO_CHECK = totalUnidentifiedSegments ?? 10000; // Safety limit
    let segments: Array<{
      id: string;
      processing_run_id: string;
      clip_url: string | null;
      vertical_clip_url: string | null;
      thumbnail_url: string | null;
      transcript: string | null;
      duration_seconds: number | null;
      speaker: string | null;
      is_unidentified: boolean | null;
      member_id: number | null;
      asd_num_faces_saved: number | null;
      start_seconds: number | null;
      end_seconds: number | null;
      mp_id_match_diagnostics: unknown;
      event_processing_runs: {
        id: string;
        parliament_events: {
          session_date: string | null;
          session_start_time: string | null;
          event_url: string | null;
        } | null;
      } | null;
    }> | null = null;
    let batchOffset = 0;
    let segmentsChecked = 0;

    while (segmentsChecked < MAX_SEGMENTS_TO_CHECK) {
      const { data: batchSegments, error: segmentsError } =
        await supabaseAdminClient
          .from("event_processing_segments")
          .select(
            `
            id,
            processing_run_id,
            clip_url,
            vertical_clip_url,
            thumbnail_url,
            transcript,
            duration_seconds,
            speaker,
            is_unidentified,
            member_id,
            asd_num_faces_saved,
            start_seconds,
            end_seconds,
            mp_id_match_diagnostics,
            event_processing_runs!inner (
              id,
              parliament_events!inner (
                session_date,
                session_start_time,
                event_url
              )
            )
          `
          )
          .in("processing_run_id", EVALUATION_PROCESSING_RUN_IDS)
          .is("member_id", null) // Unidentified segments only (member_id IS NULL)
          .is("manually_assigned_member_id", null) // Not yet manually identified
          .gt("asd_num_faces_saved", 0)
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

      // Check for locks on these segments (completion status is tracked via manually_assigned_member_id)
      const segmentIds = segments.map((s) => s.id);
      const { data: existingEvaluations, error: evalError } =
        await supabaseAdminClient
          .from("portrait_collection_evaluations")
          .select(
            "segment_id, locked_by, locked_at, skip_reason, member_id_selected"
          )
          .in("segment_id", segmentIds);

      if (evalError) {
        console.error("Error fetching evaluation locks:", evalError);
        return NextResponse.json(
          { error: "Failed to check locks" },
          { status: 500 }
        );
      }

      // Build a map of segment_id to lock status
      const evaluationMap = new Map(
        existingEvaluations?.map((e) => [e.segment_id, e]) ?? []
      );

      // Two-pass strategy:
      // 1st pass: Prioritize completely unlocked segments
      // 2nd pass: Only if no unlocked found, use segments with expired locks (oldest first)
      let selectedSegment = null;
      const expiredLockSegments: Array<{
        segment: (typeof segments)[0];
        lockedAt: string;
      }> = [];

      // First pass: Find unlocked segments
      for (const segment of segments) {
        const evaluation = evaluationMap.get(segment.id);

        // Skip segments that have been completed or skipped
        if (evaluation?.skip_reason || evaluation?.member_id_selected) {
          continue;
        }

        // If no evaluation record at all, or locked by current user, it's available
        if (
          !evaluation ||
          !evaluation.locked_by ||
          evaluation.locked_by === user.id
        ) {
          selectedSegment = segment;
          break;
        }

        // If locked by another user, check if lock expired
        if (
          evaluation.locked_by &&
          evaluation.locked_by !== user.id &&
          evaluation.locked_at
        ) {
          const lockTime = new Date(evaluation.locked_at);
          const expiryTime = new Date(lockExpiry);

          if (lockTime <= expiryTime) {
            // Lock has expired, add to candidates (only if not skipped/completed)
            if (!evaluation.skip_reason && !evaluation.member_id_selected) {
              expiredLockSegments.push({
                segment,
                lockedAt: evaluation.locked_at,
              });
            }
          }
        }
      }

      // Second pass: If no unlocked segment found, use oldest expired lock
      if (!selectedSegment && expiredLockSegments.length > 0) {
        // Sort by locked_at ascending (oldest first)
        expiredLockSegments.sort(
          (a, b) =>
            new Date(a.lockedAt).getTime() - new Date(b.lockedAt).getTime()
        );
        selectedSegment = expiredLockSegments[0].segment;
      }

      if (selectedSegment) {
        // Found an available segment, break out of the loop
        segments = [selectedSegment];
        break;
      }
      // All segments in this batch were unavailable, try next batch
    }

    if (!segments || segments.length === 0) {
      return NextResponse.json({
        success: true,
        complete: true,
        message: "No segments available for portrait collection",
      });
    }

    // Use the selected segment
    const selectedSegment = segments[0];

    // Fetch evaluation for this segment to check lock status
    const { data: existingEvalData } = await supabaseAdminClient
      .from("portrait_collection_evaluations")
      .select("locked_by, locked_at, skip_reason, member_id_selected")
      .eq("segment_id", selectedSegment.id)
      .maybeSingle();

    const existingEval = existingEvalData || null;

    // Lock the segment atomically

    if (existingEval) {
      // Update existing record - but only if it's truly available
      // Check that it's either unlocked OR locked by current user OR lock expired
      const canLock =
        !existingEval.locked_by ||
        existingEval.locked_by === user.id ||
        (existingEval.locked_at &&
          new Date(existingEval.locked_at) <= new Date(lockExpiry));

      if (!canLock) {
        // Segment was just locked by another user, return conflict
        return NextResponse.json(
          { error: "Segment was just locked by another user" },
          { status: 409 }
        );
      }

      // Atomically update the lock
      const { data: updateData, error: updateError } = await supabaseAdminClient
        .from("portrait_collection_evaluations")
        .update({
          locked_by: user.id,
          locked_at: new Date().toISOString(),
        })
        .eq("segment_id", selectedSegment.id)
        .is("member_id_selected", null) // Only lock if not yet completed (NULL placeholder)
        .is("skip_reason", null) // Only lock if not yet skipped
        .or(
          `locked_by.is.null,locked_by.eq.${user.id},locked_at.lt.${lockExpiry}`
        )
        .select();

      // If no rows were updated, another user got the lock first
      if (updateError || !updateData || updateData.length === 0) {
        console.warn("Failed to acquire lock, another user got it first");
        return NextResponse.json(
          { error: "Segment was just locked, fetching next one" },
          { status: 409 }
        );
      }
    } else {
      // Insert new record with lock
      const { error: insertError } = await supabaseAdminClient
        .from("portrait_collection_evaluations")
        .insert({
          segment_id: selectedSegment.id,
          processing_run_id: selectedSegment.processing_run_id,
          evaluated_by: user.id,
          locked_by: user.id,
          locked_at: new Date().toISOString(),
          member_id_selected: null, // Placeholder - will be updated when user submits
          selected_face_indices: [-1], // Placeholder to satisfy CHECK constraint
          rejected_face_indices: [],
          portraits_added: [],
        });

      if (insertError) {
        console.error(
          "INSERT ERROR for segment:",
          selectedSegment.id,
          "Error details:",
          insertError
        );
        return NextResponse.json(
          { error: "Segment was just evaluated, fetching next one" },
          { status: 409 }
        );
      }
    }

    // Fetch speaker faces for this segment
    const { data: speakerFaces, error: facesError } = await supabaseAdminClient
      .from("segment_speaker_faces")
      .select(
        `
        id,
        s3_url,
        face_index,
        quality_score,
        confidence,
        is_frontal,
        occlusion_score,
        face_size
      `
      )
      .eq("segment_id", selectedSegment.id)
      .order("face_index", { ascending: true });

    if (facesError) {
      console.error("Error fetching speaker faces:", facesError);
    }

    // Get top candidates from mp_id_match_diagnostics JSONB field
    // This contains pre-computed top 3 candidates with vote counts and similarity scores
    interface DiagnosticsCandidate {
      mp_id: number;
      vote_count: number;
      avg_similarity: number;
    }

    const diagnostics = selectedSegment.mp_id_match_diagnostics as {
      top_3_candidates?: DiagnosticsCandidate[];
    } | null;

    const diagnosticsCandidates = diagnostics?.top_3_candidates ?? [];

    // Fetch MP details for the candidates from diagnostics
    const candidateMemberIds = diagnosticsCandidates.map((c) => c.mp_id);

    let memberDetails: Array<{
      member_id: number;
      display_name: string | null;
      party_name: string | null;
      party_abbreviation: string | null;
      constituency_name: string | null;
    }> = [];

    if (candidateMemberIds.length > 0) {
      const { data: members, error: membersError } = await supabaseAdminClient
        .from("parliament_members")
        .select(
          "member_id, display_name, party_name, party_abbreviation, constituency_name"
        )
        .in("member_id", candidateMemberIds);

      if (membersError) {
        console.error("Error fetching candidate members:", membersError);
      } else {
        memberDetails = members ?? [];
      }
    }

    // For each candidate, fetch their portraits with Parliament-first + fallback strategy
    const topCandidates: MPCandidate[] = [];

    for (const candidate of diagnosticsCandidates) {
      const member = memberDetails.find((m) => m.member_id === candidate.mp_id);
      if (!member) continue;

      // Fetch ALL portraits for this member
      const { data: allPortraits } = await supabaseAdminClient
        .from("parliament_member_portraits")
        .select("id, image_url, crop_type, is_primary")
        .eq("member_id", member.member_id)
        .eq("is_deleted", false);

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

      // Take first 4 parliament portraits
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
          isPrimary: p.is_primary,
        };
      });

      topCandidates.push({
        memberId: member.member_id,
        displayName: member.display_name ?? "",
        partyName: member.party_name ?? null,
        partyAbbreviation: member.party_abbreviation ?? "",
        constituencyName: member.constituency_name ?? null,
        similarity: candidate.avg_similarity ?? 0,
        portraits: transformedPortraits,
      });
    }

    const segment: UnidentifiedSegment = {
      segmentId: selectedSegment.id,
      processingRunId: selectedSegment.processing_run_id,
      clipUrl: selectedSegment.clip_url,
      verticalClipUrl: selectedSegment.vertical_clip_url,
      thumbnailUrl: selectedSegment.thumbnail_url,
      transcript: selectedSegment.transcript,
      durationSeconds: selectedSegment.duration_seconds,
      speaker: selectedSegment.speaker,
      sessionDate:
        selectedSegment.event_processing_runs?.parliament_events
          ?.session_date || null,
      sessionStartTime:
        selectedSegment.event_processing_runs?.parliament_events
          ?.session_start_time || null,
      startSeconds: selectedSegment.start_seconds ?? null,
      endSeconds: selectedSegment.end_seconds ?? null,
      eventUrl:
        selectedSegment.event_processing_runs?.parliament_events?.event_url ||
        null,
      speakerFaces:
        speakerFaces?.map(
          (f): SpeakerFace => ({
            id: f.id,
            s3Url: f.s3_url ?? "",
            faceIndex: f.face_index,
            qualityScore: f.quality_score,
            confidence: f.confidence,
            isFrontal: f.is_frontal,
            occlusionScore: f.occlusion_score,
            faceSize: f.face_size,
          })
        ) ?? [],
      topCandidates,
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
