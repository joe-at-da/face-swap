import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { EVALUATION_PROCESSING_RUN_IDS } from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";

export interface SpeakerFace {
  id: string;
  s3Url: string;
  faceIndex: number;
  qualityScore: number | null;
  isFrontal: boolean | null;
}

export interface FailedEvaluationResult {
  segmentId: string;
  clipUrl: string | null;
  thumbnailUrl: string | null;
  transcript: string | null;
  speaker: string | null;
  errorReason: string | null;
  detectedMemberId: number | null;
  detectedMemberName: string | null;
  detectedPartyName: string | null;
  detectedConstituencyName: string | null;
  manuallyAssignedMemberId: number | null;
  manuallyAssignedMemberName: string | null;
  manuallyAssignedPartyName: string | null;
  manuallyAssignedConstituencyName: string | null;
  evaluatedAt: string | null;
  evaluatedBy: string | null;
  speakerFaces: SpeakerFace[];
  mpIdReason: string | null;
}

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
        results: [],
        message: "No processing runs configured for evaluation",
      });
    }

    // Fetch failed evaluations with pagination to handle >1000 rows
    const PAGE_SIZE = 1000;
    // Use smaller batch size for .in() queries to avoid "URI too long" errors
    const IN_CLAUSE_BATCH_SIZE = 100;
    let allEvaluations: Array<{
      segment_id: string;
      error_reason: string | null;
      created_at: string | null;
      evaluated_by: string | null;
    }> = [];
    let evaluationsPage = 0;
    let hasMoreEvaluations = true;

    while (hasMoreEvaluations) {
      const { data: evaluations, error: evaluationsError } =
        await supabaseAdminClient
          .from("segment_evaluations")
          .select(
            `
            segment_id,
            error_reason,
            created_at,
            evaluated_by
          `
          )
          .in("processing_run_id", EVALUATION_PROCESSING_RUN_IDS)
          .eq("is_correct", false)
          .order("created_at", { ascending: false })
          .range(
            evaluationsPage * PAGE_SIZE,
            (evaluationsPage + 1) * PAGE_SIZE - 1
          );

      if (evaluationsError) {
        console.error("Error fetching evaluations:", evaluationsError);
        return NextResponse.json(
          { error: "Failed to fetch evaluations" },
          { status: 500 }
        );
      }

      if (evaluations && evaluations.length > 0) {
        allEvaluations = allEvaluations.concat(evaluations);
        hasMoreEvaluations = evaluations.length === PAGE_SIZE;
        evaluationsPage++;
      } else {
        hasMoreEvaluations = false;
      }
    }

    const evaluations = allEvaluations;

    if (!evaluations || evaluations.length === 0) {
      return NextResponse.json({
        success: true,
        results: [],
        message: "No failed evaluations found",
      });
    }

    // Fetch segment details for all failed evaluations with pagination to handle >1000 IDs
    const segmentIds = evaluations
      .map((e) => e.segment_id)
      .filter((id): id is string => Boolean(id)); // Filter out null/undefined IDs
    
    if (segmentIds.length === 0) {
      return NextResponse.json({
        success: true,
        results: [],
        message: "No valid segment IDs found in evaluations",
      });
    }
    
    let allSegments: Array<{
      id: string;
      clip_url: string | null;
      thumbnail_url: string | null;
      transcript: string | null;
      speaker: string | null;
      member_id: number | null;
      manually_assigned_member_id: number | null;
      mp_id_reason: string | null;
    }> = [];
    let segmentsPage = 0;
    let hasMoreSegments = true;

    while (hasMoreSegments) {
      const segmentIdsPage = segmentIds.slice(
        segmentsPage * IN_CLAUSE_BATCH_SIZE,
        (segmentsPage + 1) * IN_CLAUSE_BATCH_SIZE
      );

      if (segmentIdsPage.length === 0) {
        hasMoreSegments = false;
        break;
      }

      const { data: segments, error: segmentsError } = await supabaseAdminClient
        .from("event_processing_segments")
        .select(
          "id, clip_url, thumbnail_url, transcript, speaker, member_id, manually_assigned_member_id, mp_id_reason"
        )
        .in("id", segmentIdsPage);

      if (segmentsError) {
        console.error("Error fetching segments:", segmentsError);
        console.error("Segment IDs being queried:", segmentIdsPage.slice(0, 10), "...");
        return NextResponse.json(
          { 
            error: "Failed to fetch segments",
            details: segmentsError.message || String(segmentsError),
            segmentIdsCount: segmentIdsPage.length
          },
          { status: 500 }
        );
      }

      if (segments && segments.length > 0) {
        allSegments = allSegments.concat(segments);
        hasMoreSegments = segmentIdsPage.length === IN_CLAUSE_BATCH_SIZE;
        segmentsPage++;
      } else {
        hasMoreSegments = false;
      }
    }

    const segments = allSegments;

    // Build map of segment data
    const segmentMap = new Map(segments?.map((s) => [s.id, s]) ?? []);

    // Fetch speaker faces for all segments with pagination to handle >1000 IDs
    let allSpeakerFaces: Array<{
      id: string;
      s3_url: string | null;
      face_index: number;
      quality_score: number | null;
      is_frontal: boolean | null;
      segment_id: string;
    }> = [];
    let speakerFacesPage = 0;
    let hasMoreSpeakerFaces = true;

    while (hasMoreSpeakerFaces) {
      const segmentIdsPage = segmentIds.slice(
        speakerFacesPage * IN_CLAUSE_BATCH_SIZE,
        (speakerFacesPage + 1) * IN_CLAUSE_BATCH_SIZE
      );

      if (segmentIdsPage.length === 0) {
        hasMoreSpeakerFaces = false;
        break;
      }

      const { data: speakerFaces, error: speakerFacesError } =
        await supabaseAdminClient
          .from("segment_speaker_faces")
          .select(
            "id, s3_url, face_index, quality_score, is_frontal, segment_id"
          )
          .in("segment_id", segmentIdsPage)
          .order("face_index", { ascending: true });

      if (speakerFacesError) {
        console.error("Error fetching speaker faces:", speakerFacesError);
        // Don't fail the whole request if speaker faces fail
      } else if (speakerFaces && speakerFaces.length > 0) {
        allSpeakerFaces = allSpeakerFaces.concat(speakerFaces);
      }

      hasMoreSpeakerFaces = segmentIdsPage.length === IN_CLAUSE_BATCH_SIZE;
      speakerFacesPage++;
    }

    const speakerFaces = allSpeakerFaces;

    // Build map of speaker faces by segment ID
    const speakerFacesMap = new Map<string, SpeakerFace[]>();
    speakerFaces?.forEach((face) => {
      if (!speakerFacesMap.has(face.segment_id)) {
        speakerFacesMap.set(face.segment_id, []);
      }
      speakerFacesMap.get(face.segment_id)!.push({
        id: face.id,
        s3Url: face.s3_url ?? "",
        faceIndex: face.face_index,
        qualityScore: face.quality_score,
        isFrontal: face.is_frontal,
      });
    });

    // Get all unique member IDs (both detected and manually assigned)
    const memberIds = new Set<number>();
    segments?.forEach((s) => {
      if (s.member_id) memberIds.add(s.member_id);
      if (s.manually_assigned_member_id)
        memberIds.add(s.manually_assigned_member_id);
    });

    // Fetch member details for all members with pagination to handle >1000 IDs
    const memberIdsArray = Array.from(memberIds);
    let allMembers: Array<{
      member_id: number;
      display_name: string | null;
      party_name: string | null;
      constituency_name: string | null;
    }> = [];
    let membersPage = 0;
    let hasMoreMembers = true;

    while (hasMoreMembers) {
      const memberIdsPage = memberIdsArray.slice(
        membersPage * IN_CLAUSE_BATCH_SIZE,
        (membersPage + 1) * IN_CLAUSE_BATCH_SIZE
      );

      if (memberIdsPage.length === 0) {
        hasMoreMembers = false;
        break;
      }

      const { data: members, error: membersError } = await supabaseAdminClient
        .from("parliament_members")
        .select("member_id, display_name, party_name, constituency_name")
        .in("member_id", memberIdsPage);

      if (membersError) {
        console.error("Error fetching members:", membersError);
        // Don't fail the whole request if members fail, but log the error
      } else if (members && members.length > 0) {
        allMembers = allMembers.concat(members);
      }

      hasMoreMembers = memberIdsPage.length === IN_CLAUSE_BATCH_SIZE;
      membersPage++;
    }

    const members = allMembers;

    // Build map of member data
    const memberMap = new Map(members?.map((m) => [m.member_id, m]) ?? []);

    // Combine all data into results
    const results: FailedEvaluationResult[] = evaluations.map((evaluation) => {
      const segment = segmentMap.get(evaluation.segment_id);
      const detectedMember = segment?.member_id
        ? memberMap.get(segment.member_id)
        : null;
      const manuallyAssignedMember = segment?.manually_assigned_member_id
        ? memberMap.get(segment.manually_assigned_member_id)
        : null;
      const faces = speakerFacesMap.get(evaluation.segment_id) ?? [];

      return {
        segmentId: evaluation.segment_id,
        clipUrl: segment?.clip_url ?? null,
        thumbnailUrl: segment?.thumbnail_url ?? null,
        transcript: segment?.transcript ?? null,
        speaker: segment?.speaker ?? null,
        errorReason: evaluation.error_reason,
        detectedMemberId: segment?.member_id ?? null,
        detectedMemberName: detectedMember?.display_name ?? null,
        detectedPartyName: detectedMember?.party_name ?? null,
        detectedConstituencyName: detectedMember?.constituency_name ?? null,
        manuallyAssignedMemberId: segment?.manually_assigned_member_id ?? null,
        manuallyAssignedMemberName:
          manuallyAssignedMember?.display_name ?? null,
        manuallyAssignedPartyName: manuallyAssignedMember?.party_name ?? null,
        manuallyAssignedConstituencyName:
          manuallyAssignedMember?.constituency_name ?? null,
        evaluatedAt: evaluation.created_at,
        evaluatedBy: evaluation.evaluated_by,
        speakerFaces: faces,
        mpIdReason: segment?.mp_id_reason ?? null,
      };
    });

    return NextResponse.json({
      success: true,
      results,
      total: results.length,
    });
  } catch (error) {
    console.error("Results fetch error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch results: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
