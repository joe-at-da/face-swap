import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";

export async function GET(request: NextRequest) {
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

    // Parse query parameters
    const searchParams = request.nextUrl.searchParams;
    const page = parseInt(searchParams.get("page") || "1");
    const limit = parseInt(searchParams.get("limit") || "20");
    const status = searchParams.get("status");
    const search = searchParams.get("search");
    const sortBy = searchParams.get("sortBy") || "created_at";
    const sortOrder = searchParams.get("sortOrder") || "desc";
    const dateFrom = searchParams.get("dateFrom");
    const dateTo = searchParams.get("dateTo");
    const teamId = searchParams.get("teamId");

    // If teamId is provided, verify user is a member of the team
    if (teamId) {
      const { data: userRole } = await supabase.rpc("get_team_role", {
        p_user_id: user.id,
        p_team_id: teamId,
      });

      if (!userRole) {
        return NextResponse.json(
          { error: "You are not a member of this team" },
          { status: 403 }
        );
      }
    }

    // Calculate offset for pagination
    const offset = (page - 1) * limit;

    // Build query with joins to get MP information
    let query = supabase
      .from("user_clips")
      .select(
        `
        *,
        parliament_member_clips!inner(
          id,
          member_id,
          session_date,
          parliament_members!inner(
            display_name,
            party_name,
            party_abbreviation
          )
        )
      `
      )
      .eq("is_deleted", false);

    // Filter by team_id if provided, otherwise filter by user_id and team_id IS NULL (personal clips)
    if (teamId) {
      query = query.eq("team_id", teamId);
    } else {
      query = query.eq("user_id", user.id).is("team_id", null);
    }

    // Apply filters
    if (status) {
      query = query.eq(
        "status",
        status as "processing" | "completed" | "failed" | "pending_review"
      );
    }

    // Apply search if provided (search in title, description, and transcript)
    if (search && search.length > 2) {
      query = query.or(
        `title.ilike.%${search}%,description.ilike.%${search}%,transcript.ilike.%${search}%`
      );
    }

    // Apply date range filter if provided
    if (dateFrom) {
      query = query.gte("created_at", dateFrom);
    }
    if (dateTo) {
      // Add end of day to dateTo for inclusive filtering
      const endOfDay = new Date(dateTo);
      endOfDay.setHours(23, 59, 59, 999);
      query = query.lte("created_at", endOfDay.toISOString());
    }

    // Apply sorting
    query = query.order(sortBy, { ascending: sortOrder === "asc" });

    // Apply pagination
    const { data: clips, error: clipsError } = await query.range(
      offset,
      offset + limit - 1
    );

    if (clipsError) {
      console.error("Failed to fetch user clips:", clipsError);
      return NextResponse.json(
        { error: "Failed to fetch clips" },
        { status: 500 }
      );
    }

    // Get total count for pagination with same filters
    let countQuery = supabase
      .from("user_clips")
      .select("*", { count: "exact", head: true })
      .eq("is_deleted", false);

    // Filter by team_id if provided, otherwise filter by user_id and team_id IS NULL (personal clips)
    if (teamId) {
      countQuery = countQuery.eq("team_id", teamId);
    } else {
      countQuery = countQuery.eq("user_id", user.id).is("team_id", null);
    }

    // Apply same filters to count query
    if (status) {
      countQuery = countQuery.eq(
        "status",
        status as "processing" | "completed" | "failed" | "pending_review"
      );
    }
    if (dateFrom) {
      countQuery = countQuery.gte("created_at", dateFrom);
    }
    if (dateTo) {
      const endOfDay = new Date(dateTo);
      endOfDay.setHours(23, 59, 59, 999);
      countQuery = countQuery.lte("created_at", endOfDay.toISOString());
    }

    const { count, error: countError } = await countQuery;

    if (countError) {
      console.error("Failed to count user clips:", countError);
      return NextResponse.json(
        { error: "Failed to count clips" },
        { status: 500 }
      );
    }

    // Calculate pagination metadata
    const totalPages = Math.ceil((count || 0) / limit);
    const hasNextPage = page < totalPages;
    const hasPreviousPage = page > 1;

    return NextResponse.json({
      success: true,
      data: clips,
      pagination: {
        currentPage: page,
        totalPages,
        totalItems: count || 0,
        hasNextPage,
        hasPreviousPage,
        itemsPerPage: limit,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("User clips API error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch user clips: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
