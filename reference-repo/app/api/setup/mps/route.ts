import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();
    
    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const search = searchParams.get('search') || '';

    // Fetch current MPs with their portraits
    let query = supabase
      .from("parliament_members")
      .select(`
        member_id,
        display_name,
        party_abbreviation,
        party_name,
        constituency_name,
        parliament_member_portraits!inner (
          image_url,
          is_primary
        )
      `)
      .eq("is_current_member", true)
      .eq("is_deleted", false)
      .eq("parliament_member_portraits.is_deleted", false)
      .eq("parliament_member_portraits.is_primary", true)
      .order("display_name");

    // Add search filter if provided (case-insensitive, fuzzy search across multiple fields)
    if (search) {
      // Check if search term is numeric (member_id search)
      const numericSearch = parseInt(search, 10);

      if (!isNaN(numericSearch)) {
        // If numeric, search by member_id or display_name
        query = query.or(`member_id.eq.${numericSearch},display_name.ilike.%${search}%`);
      } else {
        // Search across display_name, party_abbreviation, party_name, and constituency_name
        query = query.or(
          `display_name.ilike.%${search}%,party_abbreviation.ilike.%${search}%,party_name.ilike.%${search}%,constituency_name.ilike.%${search}%`
        );
      }
    }

    const { data: mps, error } = await query.limit(50);

    if (error) {
      throw error;
    }

    return NextResponse.json({
      mps: mps || []
    });

  } catch (error) {
    console.error("MPs fetch error:", error);
    return NextResponse.json(
      { error: handleError(error, {
        component: 'api/setup/mps',
        action: 'GET',
        route: '/api/setup/mps',
      }) },
      { status: 500 }
    );
  }
}