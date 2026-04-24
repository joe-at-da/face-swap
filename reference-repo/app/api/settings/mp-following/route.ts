import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { captureServerEvent } from "@/lib/posthog-server";

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
      member_id: number;
    };
    
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { member_id } = body;

    // Validate member_id
    if (!member_id || typeof member_id !== "number") {
      return NextResponse.json(
        { error: "Valid member_id is required" },
        { status: 400 }
      );
    }

    // Verify the MP exists and is eligible
    const { data: mp, error: mpError } = await supabaseAdminClient
      .from("parliament_members")
      .select("member_id, display_name, is_eligible")
      .eq("member_id", member_id)
      .eq("is_deleted", false)
      .single();

    if (mpError || !mp) {
      return NextResponse.json(
        { error: "MP not found or invalid" },
        { status: 404 }
      );
    }

    if (!mp.is_eligible) {
      return NextResponse.json(
        { error: "This MP is not available for following" },
        { status: 400 }
      );
    }

    // Check if user already has a profile setup (for potential future use)
    const { data: existingRole, error: roleCheckError } = await supabaseAdminClient
      .from("user_roles")
      .select("user_id, member_id")
      .eq("user_id", user.id)
      .single();
    
    console.log(`User ${user.id} profile update: ${existingRole ? 'updating' : 'creating'} MP following`);

    if (roleCheckError && roleCheckError.code !== 'PGRST116') {
      console.error("Failed to check existing user role:", roleCheckError);
      return NextResponse.json(
        { error: "Failed to update MP following" },
        { status: 500 }
      );
    }

    // Update or insert the user role with new MP
    const { error: updateError } = await (supabaseAdminClient
      .from("user_roles") as 
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      any)
      .upsert({
        user_id: user.id,
        member_id: member_id,
        updated_at: new Date().toISOString()
      });

    if (updateError) {
      console.error("Failed to update MP following:", updateError);
      return NextResponse.json(
        { error: "Failed to update MP following" },
        { status: 500 }
      );
    }

    console.log(`[MP Following API] User ${user.id} now following MP ${member_id} (${mp.display_name})`);

    // Track MP followed event
    try {
      await captureServerEvent(user.id, "mp_followed", {
        member_id: member_id,
        mp_name: mp.display_name,
        previous_mp_id: existingRole?.member_id || null,
      });
    } catch (trackingError) {
      console.error("PostHog mp_followed event capture failed:", trackingError);
    }

    return NextResponse.json({
      success: true,
      message: `Now following ${mp.display_name}`,
      data: {
        member_id: member_id,
        mp_name: mp.display_name,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Update MP following error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to update MP following: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

// Get list of available MPs for following
export async function GET(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user (to ensure they're logged in)
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Get query parameters
    const searchParams = request.nextUrl.searchParams;
    const search = searchParams.get("search");
    const party = searchParams.get("party");

    // Build query for available MPs
    let query = supabaseAdminClient
      .from("parliament_members")
      .select(`
        member_id,
        display_name,
        party_name,
        party_abbreviation,
        constituency_name,
        house_name
      `)
      .eq("is_deleted", false)
      .eq("is_eligible", true)
      .order("display_name");

    // Apply search filter
    if (search && search.length > 1) {
      query = query.or(`display_name.ilike.%${search}%,party_name.ilike.%${search}%,constituency_name.ilike.%${search}%`);
    }

    // Apply party filter
    if (party) {
      query = query.eq("party_abbreviation", party);
    }

    const { data: mps, error: mpsError } = await query.limit(100);

    if (mpsError) {
      console.error("Failed to fetch MPs:", mpsError);
      return NextResponse.json(
        { error: "Failed to fetch available MPs" },
        { status: 500 }
      );
    }

    // Get unique parties for filtering
    const { data: parties } = await supabaseAdminClient
      .from("parliament_members")
      .select("party_abbreviation, party_name")
      .eq("is_deleted", false)
      .eq("is_eligible", true)
      .not("party_abbreviation", "is", null)
      .order("party_name");

    const uniqueParties = parties?.reduce((acc: Array<{
      abbreviation: string | null;
      name: string | null;
    }>, curr) => {
      if (!acc.find(p => p.abbreviation === curr.party_abbreviation)) {
        acc.push({
          abbreviation: curr.party_abbreviation,
          name: curr.party_name,
        });
      }
      return acc;
    }, []) || [];

    return NextResponse.json({
      success: true,
      data: {
        mps: mps || [],
        parties: uniqueParties,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Get available MPs error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch available MPs: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}