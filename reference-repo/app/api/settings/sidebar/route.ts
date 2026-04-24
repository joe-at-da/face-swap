import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

export async function PUT(request: NextRequest) {
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
    let body: {
      collapsed?: boolean;
    };

    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { collapsed } = body;

    // Validate input
    if (typeof collapsed !== "boolean") {
      return NextResponse.json(
        { error: "collapsed must be a boolean value" },
        { status: 400 }
      );
    }

    // Update user metadata for sidebar preference
    const { error: metadataError } = await supabaseAdminClient.auth.admin.updateUserById(
      user.id,
      {
        user_metadata: {
          ...user.user_metadata,
          sidebar_collapsed: collapsed,
        }
      }
    );

    if (metadataError) {
      console.error("Failed to update sidebar preference:", metadataError);
      return NextResponse.json(
        { error: "Failed to update sidebar preference" },
        { status: 500 }
      );
    }

    console.log(`[Sidebar API] Updated sidebar preference for user ${user.id}`, {
      collapsed
    });

    return NextResponse.json({
      success: true,
      message: "Sidebar preference updated successfully",
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Update sidebar preference error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to update sidebar preference: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
