import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

interface UnlockBody {
  segmentId: string;
}

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

    // Parse request body
    let body: UnlockBody;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { segmentId } = body;

    // Validate segmentId
    if (!segmentId || typeof segmentId !== "string") {
      return NextResponse.json(
        { error: "segmentId is required and must be a string" },
        { status: 400 }
      );
    }

    // Clear the lock only if it was locked by the current user and not yet evaluated
    const { error: unlockError } = await supabaseAdminClient
      .from("segment_evaluations")
      .update({
        locked_by: null,
        locked_at: null,
        updated_at: new Date().toISOString(),
      })
      .eq("segment_id", segmentId)
      .eq("locked_by", user.id)
      .is("is_correct", null); // Only unlock if not yet evaluated

    if (unlockError) {
      console.error("Error unlocking segment:", unlockError);
      return NextResponse.json(
        { error: "Failed to unlock segment" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Segment unlocked successfully",
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
