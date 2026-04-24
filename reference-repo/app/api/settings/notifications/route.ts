import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { ErrorLogger } from "@/lib/errorLogger";

export async function GET() {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { data, error } = await supabaseAdminClient
      .from("user_roles")
      .select("new_clips_available")
      .eq("user_id", user.id)
      .single();

    if (error) {
      ErrorLogger.logDatabaseError(error, "get_notification_settings", "user_roles", user.id);
      return NextResponse.json(
        { error: "Failed to fetch notification settings" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data: { new_clips_available: data.new_clips_available },
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: `Failed to fetch notification settings: ${errorMessage}` },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    let body: { new_clips_available?: boolean };

    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    if (typeof body.new_clips_available !== "boolean") {
      return NextResponse.json(
        { error: "new_clips_available must be a boolean" },
        { status: 400 }
      );
    }

    const { error } = await supabaseAdminClient
      .from("user_roles")
      .update({ new_clips_available: body.new_clips_available })
      .eq("user_id", user.id);

    if (error) {
      ErrorLogger.logDatabaseError(error, "update_notification_settings", "user_roles", user.id);
      return NextResponse.json(
        { error: "Failed to update notification settings" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Notification settings updated",
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: `Failed to update notification settings: ${errorMessage}` },
      { status: 500 }
    );
  }
}
