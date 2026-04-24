import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

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

    // Get user role data (only member_id - names and avatar are in metadata)
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select(`
        member_id,
        parliament_members(
          display_name,
          party_name,
          party_abbreviation,
          constituency_name
        )
      `)
      .eq("user_id", user.id)
      .single();

    // Don't error if user role doesn't exist - user might not have selected an MP yet
    if (userRoleError && userRoleError.code !== 'PGRST116') {
      console.error("Failed to fetch user profile:", userRoleError);
      return NextResponse.json(
        { error: "Failed to fetch profile" },
        { status: 500 }
      );
    }

    // Combine auth user data with metadata and user role data
    const profileData = {
      id: user.id,
      email: user.email,
      created_at: user.created_at,
      updated_at: user.updated_at,
      // Get name and avatar from user metadata
      first_name: user.user_metadata?.first_name || null,
      last_name: user.user_metadata?.last_name || null,
      avatar_url: user.user_metadata?.profile_image || user.user_metadata?.avatar_url || null,
      // Get MP data from user_roles table if exists
      member_id: userRole?.member_id || null,
      parliament_members: userRole?.parliament_members || null,
    };

    return NextResponse.json({
      success: true,
      data: profileData,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Get profile error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch profile: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

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
      first_name?: string;
      last_name?: string;
      avatar_url?: string;
    };
    
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { first_name, last_name, avatar_url } = body;

    // Validate input
    if (first_name && (typeof first_name !== "string" || first_name.length > 100)) {
      return NextResponse.json(
        { error: "First name must be a string with max 100 characters" },
        { status: 400 }
      );
    }

    if (last_name && (typeof last_name !== "string" || last_name.length > 100)) {
      return NextResponse.json(
        { error: "Last name must be a string with max 100 characters" },
        { status: 400 }
      );
    }

    if (avatar_url && (typeof avatar_url !== "string" || !isValidUrl(avatar_url))) {
      return NextResponse.json(
        { error: "Avatar URL must be a valid URL" },
        { status: 400 }
      );
    }

    // Update user metadata for first_name, last_name, and avatar_url
    const metadataUpdates: Record<string, string> = {};
    if (first_name !== undefined) metadataUpdates.first_name = first_name;
    if (last_name !== undefined) metadataUpdates.last_name = last_name;
    if (avatar_url !== undefined) {
      // Store as profile_image in metadata to match setup page pattern
      metadataUpdates.profile_image = avatar_url;
      metadataUpdates.avatar_url = avatar_url; // Keep both for compatibility
    }

    if (Object.keys(metadataUpdates).length === 0) {
      return NextResponse.json(
        { error: "No valid fields provided for update" },
        { status: 400 }
      );
    }

    // Update user metadata
    const { error: metadataError } = await supabaseAdminClient.auth.admin.updateUserById(
      user.id,
      {
        user_metadata: {
          ...user.user_metadata,
          ...metadataUpdates,
        }
      }
    );

    if (metadataError) {
      console.error("Failed to update user metadata:", metadataError);
      return NextResponse.json(
        { error: "Failed to update profile metadata" },
        { status: 500 }
      );
    }

    console.log(`[Profile API] Updated profile for user ${user.id}`, { 
      metadataUpdates: Object.keys(metadataUpdates)
    });

    return NextResponse.json({
      success: true,
      message: "Profile updated successfully",
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Update profile error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to update profile: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

function isValidUrl(string: string): boolean {
  try {
    new URL(string);
    return true;
  } catch {
    return false;
  }
}