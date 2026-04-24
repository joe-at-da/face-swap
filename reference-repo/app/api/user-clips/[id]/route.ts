import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { generateAndFormatEmbedding } from "@/services/ai/embedding-service";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createSupabaseServerClient();
    const { id } = await params;

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Validate UUID format
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
      return NextResponse.json(
        { error: "Invalid clip ID format" },
        { status: 400 }
      );
    }

    // Fetch the user clip (RLS policies will handle access control for personal/team clips)
    const { data: userClip, error: userClipError } = await supabase
      .from("user_clips")
      .select("*")
      .eq("id", id)
      .eq("is_deleted", false)
      .single();

    if (userClipError || !userClip) {
      console.error("User clip error:", userClipError);
      return NextResponse.json(
        { error: "Clip not found or access denied" },
        { status: 404 }
      );
    }

    // Fetch parliament member clip details
    const { data: parliamentClip, error: parliamentClipError } = await supabase
      .from("parliament_member_clips")
      .select(
        `
        id,
        member_id,
        full_video_path,
        session_uid
      `
      )
      .eq("id", userClip.clip_id)
      .single();

    if (parliamentClipError || !parliamentClip) {
      console.error("Parliament clip error:", parliamentClipError);
      return NextResponse.json(
        { error: "Clip details not found" },
        { status: 404 }
      );
    }

    // Fetch parliament member details
    const { data: parliamentMember, error: parliamentMemberError } =
      await supabase
        .from("parliament_members")
        .select(
          `
        display_name,
        party_name,
        party_abbreviation,
        constituency_name,
        member_id
      `
        )
        .eq("member_id", parliamentClip.member_id)
        .single();

    if (parliamentMemberError || !parliamentMember) {
      console.error("Parliament member error:", parliamentMemberError);
      return NextResponse.json(
        { error: "Member details not found" },
        { status: 404 }
      );
    }

    // Fetch parliament member portrait
    const { data: portrait } = await supabase
      .from("parliament_member_portraits")
      .select("image_url")
      .eq("member_id", parliamentClip.member_id)
      .eq("is_deleted", false)
      .eq("is_primary", true)
      .single();

    // Add portrait URL to member data if available
    const memberWithPortrait = {
      ...parliamentMember,
      profile_image: portrait?.image_url || null,
    };

    // Fetch parliament event title if session_uid is available
    let sessionName: string | null = null;
    if (parliamentClip.session_uid) {
      const { data: parliamentEvent } = await supabase
        .from("parliament_events")
        .select("title")
        .eq("event_id", parliamentClip.session_uid)
        .eq("is_deleted", false)
        .single();
      
      sessionName = parliamentEvent?.title || null;
    }

    // Combine the data
    const clip = {
      ...userClip,
      parliament_member_clips: {
        ...parliamentClip,
        parliament_members: memberWithPortrait,
        session_name: sessionName,
      },
    };

    return NextResponse.json({
      success: true,
      data: clip,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Get user clip error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch clip: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createSupabaseServerClient();
    const { id } = await params;

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Validate UUID format
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
      return NextResponse.json(
        { error: "Invalid clip ID format" },
        { status: 400 }
      );
    }

    // Soft delete the clip (RLS policies will handle access control for personal/team clips)
    const { error: deleteError } = await supabase
      .from("user_clips")
      .update({
        is_deleted: true,
        deleted_at: new Date().toISOString(),
      })
      .eq("id", id)
      .eq("is_deleted", false);

    if (deleteError) {
      console.error("Failed to delete user clip:", deleteError);
      return NextResponse.json(
        { error: "Failed to delete clip" },
        { status: 500 }
      );
    }

    console.log(`[User Clips API] Deleted clip ${id} for user ${user.id}`);

    return NextResponse.json({
      success: true,
      message: "Clip deleted successfully",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Delete user clip error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to delete clip: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createSupabaseServerClient();
    const { id } = await params;

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Validate UUID format
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
      return NextResponse.json(
        { error: "Invalid clip ID format" },
        { status: 400 }
      );
    }

    // Parse request body
    const body = await request.json();
    const { title, description, transcript } = body;

    // Validate that exactly one field is being updated
    const fieldsToUpdate = [title, description, transcript].filter(
      (field) => field !== undefined
    );
    if (fieldsToUpdate.length !== 1) {
      return NextResponse.json(
        { error: "Must update exactly one field: title, description, or transcript" },
        { status: 400 }
      );
    }

    // Fetch the user clip to check permissions
    const { data: userClip, error: userClipError } = await supabase
      .from("user_clips")
      .select("user_id, team_id")
      .eq("id", id)
      .eq("is_deleted", false)
      .single();

    if (userClipError || !userClip) {
      console.error("User clip error:", userClipError);
      return NextResponse.json(
        { error: "Clip not found or access denied" },
        { status: 404 }
      );
    }

    // Check permissions: user_id matches OR (team_id exists AND user is team member)
    const isOwner = userClip.user_id === user.id;
    let isTeamMember = false;

    if (!isOwner && userClip.team_id) {
      const { data: teamMemberCheck } = await supabase.rpc("is_team_member", {
        p_team_id: userClip.team_id,
        p_user_id: user.id,
      });
      isTeamMember = teamMemberCheck === true;
    }

    if (!isOwner && !isTeamMember) {
      return NextResponse.json(
        { error: "You do not have permission to edit this clip" },
        { status: 403 }
      );
    }

    // Prepare update object
    const updateData: {
      updated_at: string;
      title?: string;
      title_embedding?: string | null;
      description?: string;
      description_embedding?: string | null;
      transcript?: string;
      transcript_embedding?: string | null;
      transcript_manually_edited?: boolean;
    } = {
      updated_at: new Date().toISOString(),
    };

    // Handle title update
    if (title !== undefined) {
      if (typeof title !== "string") {
        return NextResponse.json(
          { error: "Title must be a string" },
          { status: 400 }
        );
      }

      updateData.title = title.trim() || undefined;

      // Generate embedding for title if it's not empty
      if (updateData.title) {
        const embeddingResult = await generateAndFormatEmbedding(updateData.title);
        if (embeddingResult.error) {
          console.error("Failed to generate title embedding:", embeddingResult.error);
          return NextResponse.json(
            { error: `Failed to generate embedding: ${embeddingResult.error}` },
            { status: 500 }
          );
        }
        updateData.title_embedding = embeddingResult.data;
      } else {
        updateData.title_embedding = null;
      }
    }

    // Handle description update
    if (description !== undefined) {
      if (typeof description !== "string") {
        return NextResponse.json(
          { error: "Description must be a string" },
          { status: 400 }
        );
      }

      updateData.description = description.trim() || undefined;

      // Generate embedding for description if it's not empty
      if (updateData.description) {
        const embeddingResult = await generateAndFormatEmbedding(updateData.description);
        if (embeddingResult.error) {
          console.error("Failed to generate description embedding:", embeddingResult.error);
          return NextResponse.json(
            { error: `Failed to generate embedding: ${embeddingResult.error}` },
            { status: 500 }
          );
        }
        updateData.description_embedding = embeddingResult.data;
      } else {
        updateData.description_embedding = null;
      }
    }

    // Handle transcript update
    if (transcript !== undefined) {
      if (typeof transcript !== "string") {
        return NextResponse.json(
          { error: "Transcript must be a string" },
          { status: 400 }
        );
      }

      updateData.transcript = transcript.trim() || undefined;

      // Validate transcript length
      if (updateData.transcript && updateData.transcript.length > 50000) {
        return NextResponse.json(
          { error: "Transcript must be 50,000 characters or less" },
          { status: 400 }
        );
      }

      // Generate embedding for transcript if it's not empty
      if (updateData.transcript) {
        // Mark as manually edited — only when a transcript will actually be persisted
        updateData.transcript_manually_edited = true;
        const embeddingResult = await generateAndFormatEmbedding(updateData.transcript);
        if (embeddingResult.error) {
          console.error("Failed to generate transcript embedding:", embeddingResult.error);
          return NextResponse.json(
            { error: `Failed to generate embedding: ${embeddingResult.error}` },
            { status: 500 }
          );
        }
        updateData.transcript_embedding = embeddingResult.data;
      } else {
        updateData.transcript_embedding = null;
      }
    }

    // Update the clip
    const { data: updatedClip, error: updateError } = await supabase
      .from("user_clips")
      .update(updateData)
      .eq("id", id)
      .select()
      .single();

    if (updateError) {
      console.error("Failed to update user clip:", updateError);
      return NextResponse.json(
        { error: "Failed to update clip" },
        { status: 500 }
      );
    }

    // Fetch parliament member clip details for response
    const { data: parliamentClip, error: parliamentClipError } = await supabase
      .from("parliament_member_clips")
      .select(
        `
        id,
        member_id,
        full_video_path,
        session_uid
      `
      )
      .eq("id", updatedClip.clip_id)
      .single();

    if (parliamentClipError || !parliamentClip) {
      console.error("Parliament clip error:", parliamentClipError);
      return NextResponse.json(
        { error: "Clip details not found" },
        { status: 404 }
      );
    }

    // Fetch parliament member details
    const { data: parliamentMember, error: parliamentMemberError } =
      await supabase
        .from("parliament_members")
        .select(
          `
        display_name,
        party_name,
        party_abbreviation,
        constituency_name,
        member_id
      `
        )
        .eq("member_id", parliamentClip.member_id)
        .single();

    if (parliamentMemberError || !parliamentMember) {
      console.error("Parliament member error:", parliamentMemberError);
      return NextResponse.json(
        { error: "Member details not found" },
        { status: 404 }
      );
    }

    // Fetch parliament member portrait
    const { data: portrait } = await supabase
      .from("parliament_member_portraits")
      .select("image_url")
      .eq("member_id", parliamentClip.member_id)
      .eq("is_deleted", false)
      .eq("is_primary", true)
      .single();

    // Add portrait URL to member data if available
    const memberWithPortrait = {
      ...parliamentMember,
      profile_image: portrait?.image_url || null,
    };

    // Fetch parliament event title if session_uid is available
    let sessionName: string | null = null;
    if (parliamentClip.session_uid) {
      const { data: parliamentEvent } = await supabase
        .from("parliament_events")
        .select("title")
        .eq("event_id", parliamentClip.session_uid)
        .eq("is_deleted", false)
        .single();
      
      sessionName = parliamentEvent?.title || null;
    }

    // Combine the data
    const clip = {
      ...updatedClip,
      parliament_member_clips: {
        ...parliamentClip,
        parliament_members: memberWithPortrait,
        session_name: sessionName,
      },
    };

    console.log(`[User Clips API] Updated clip ${id} for user ${user.id}`);

    return NextResponse.json({
      success: true,
      data: clip,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Patch user clip error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to update clip: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
