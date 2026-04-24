import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

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

    // Parse request body
    const { segmentId } = await request.json();

    if (!segmentId) {
      return NextResponse.json(
        { error: "Missing segmentId" },
        { status: 400 }
      );
    }

    // Clear lock only if:
    // 1. Locked by current user
    // 2. Not yet completed (member_id_selected IS NULL)
    const { error: unlockError } = await supabaseAdminClient
      .from("portrait_collection_evaluations")
      .update({
        locked_by: null,
        locked_at: null,
      })
      .eq("segment_id", segmentId)
      .eq("locked_by", user.id)
      .is("member_id_selected", null); // Only unlock if not completed (null placeholder)

    if (unlockError) {
      console.error("Error unlocking segment:", unlockError);
      return NextResponse.json(
        { error: "Failed to unlock segment" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
    });
  } catch (error) {
    console.error("Unlock segment error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to unlock segment: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
