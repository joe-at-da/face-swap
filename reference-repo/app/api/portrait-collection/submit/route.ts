import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import type { SubmitIdentificationRequest } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

export async function POST(request: NextRequest) {
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

    // Parse and validate request body
    const body: SubmitIdentificationRequest = await request.json();
    const {
      segmentId,
      selectedMemberId,
      selectedFaceIndices,
      rejectedFaceIndices,
    } = body;

    // Validation
    if (!segmentId || !selectedMemberId) {
      return NextResponse.json(
        { error: "Missing required fields: segmentId and selectedMemberId" },
        { status: 400 }
      );
    }

    if (!selectedFaceIndices || selectedFaceIndices.length === 0) {
      return NextResponse.json(
        { error: "Must select at least one face" },
        { status: 400 }
      );
    }

    // Fetch segment to verify it exists and get processing_run_id
    const { data: segment, error: segmentError } = await supabaseAdminClient
      .from("event_processing_segments")
      .select("id, processing_run_id")
      .eq("id", segmentId)
      .single();

    if (segmentError || !segment) {
      return NextResponse.json(
        { error: "Segment not found" },
        { status: 404 }
      );
    }

    // Fetch selected faces from segment_speaker_faces
    const { data: faces, error: facesError } = await supabaseAdminClient
      .from("segment_speaker_faces")
      .select("id, s3_url, face_index")
      .eq("segment_id", segmentId)
      .in("face_index", selectedFaceIndices);

    if (facesError || !faces || faces.length === 0) {
      return NextResponse.json(
        { error: "Selected faces not found" },
        { status: 404 }
      );
    }

    // Verify all requested face indices were found
    const foundIndices = new Set(faces.map((f) => f.face_index));
    const missingIndices = selectedFaceIndices.filter(
      (idx) => !foundIndices.has(idx)
    );

    if (missingIndices.length > 0) {
      return NextResponse.json(
        {
          error: `Face indices not found: ${missingIndices.join(", ")}`,
        },
        { status: 404 }
      );
    }

    // Verify member exists
    const { data: member, error: memberError } = await supabaseAdminClient
      .from("parliament_members")
      .select("member_id")
      .eq("member_id", selectedMemberId)
      .single();

    if (memberError || !member) {
      return NextResponse.json(
        { error: "Selected MP not found" },
        { status: 404 }
      );
    }

    // Query MAX(crop_type) for this member to get next available crop_type
    const { data: maxCropTypeData } = await supabaseAdminClient
      .from("parliament_member_portraits")
      .select("crop_type")
      .eq("member_id", selectedMemberId)
      .order("crop_type", { ascending: false })
      .limit(1);

    const maxCropType = maxCropTypeData?.[0]?.crop_type ?? -1;
    let nextCropType = maxCropType + 1;

    // Insert portraits and collect their IDs
    const portraitIds: string[] = [];

    for (const face of faces) {
      if (!face.s3_url) {
        console.warn(`Face ${face.id} has no S3 URL, skipping`);
        continue;
      }

      const { data: portrait, error: insertError } = await supabaseAdminClient
        .from("parliament_member_portraits")
        .insert({
          member_id: selectedMemberId,
          image_url: face.s3_url,
          crop_type: nextCropType,
          source: "user_uploaded",
          is_primary: false,
          is_valid_mp_image: true,
          web_version: false,
        })
        .select("id")
        .single();

      if (insertError) {
        console.error("Error inserting portrait:", insertError);
        return NextResponse.json(
          { error: "Failed to insert portrait" },
          { status: 500 }
        );
      }

      if (portrait) {
        portraitIds.push(portrait.id);
        nextCropType++; // Increment for next face
      }
    }

    // Update segment with manually assigned member ID
    const { error: updateSegmentError } = await supabaseAdminClient
      .from("event_processing_segments")
      .update({
        manually_assigned_member_id: selectedMemberId,
        manually_assigned_at: new Date().toISOString(),
        manually_assigned_by: user.id,
      })
      .eq("id", segmentId);

    if (updateSegmentError) {
      console.error("Error updating segment:", updateSegmentError);
      return NextResponse.json(
        { error: "Failed to update segment" },
        { status: 500 }
      );
    }

    // Upsert portrait_collection_evaluations record
    const { error: upsertError } = await supabaseAdminClient
      .from("portrait_collection_evaluations")
      .upsert(
        {
          segment_id: segmentId,
          processing_run_id: segment.processing_run_id,
          evaluated_by: user.id,
          member_id_selected: selectedMemberId,
          selected_face_indices: selectedFaceIndices,
          rejected_face_indices: rejectedFaceIndices,
          portraits_added: portraitIds,
          locked_by: null, // Clear lock
          locked_at: null,
        },
        {
          onConflict: "segment_id",
        }
      );

    if (upsertError) {
      console.error("Error upserting evaluation:", upsertError);
      return NextResponse.json(
        { error: "Failed to save evaluation" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      portraitIds,
      portraitCount: portraitIds.length,
    });
  } catch (error) {
    console.error("Submit identification error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to submit identification: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
