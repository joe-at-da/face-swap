import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { searchItems, getTierCounts } from "@/lib/search-utils";
// AI embedding search temporarily disabled - keeping import for future use
// import { generateEmbedding } from "@/services/ai/embedding-service";

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
    const body = await request.json();
    const { query, limit = 50, teamId } = body;

    if (!query || typeof query !== "string") {
      return NextResponse.json(
        { error: "Query parameter is required" },
        { status: 400 }
      );
    }

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

    console.log(
      `[Text Search] Performing 3-tier user clips search for query: "${query}"`
    );

    // Fetch all user clips from database
    let dbQuery = supabase
      .from("user_clips")
      .select("*, parliament_member_clips(*, parliament_members(*))")
      .eq("is_deleted", false)
      .order("created_at", { ascending: false });

    // Apply user or team filter
    if (teamId) {
      dbQuery = dbQuery.eq("team_id", teamId);
    } else {
      dbQuery = dbQuery.eq("user_id", user.id);
    }

    const { data: allClips, error: fetchError } = await dbQuery;

    if (fetchError) {
      console.error("[Text Search] Fetch error:", fetchError);
      return NextResponse.json({ error: "Fetch failed" }, { status: 500 });
    }

    const clips = allClips || [];
    console.log(`[Text Search] Fetched ${clips.length} user clips`);

    // Apply 3-tier search logic using TypeScript
    const searchResults = searchItems(clips, query, {
      getSearchFields: (clip) => [
        { value: clip.title || "", weight: 1.2 }, // Title: highest priority
        { value: clip.description || "", weight: 1.0 }, // Description: high priority
        { value: clip.transcript || "", weight: 0.5 }, // Transcript: lower priority
      ],
      getDate: (clip) => clip.created_at || new Date(0).toISOString(),
    });

    // Log tier distribution for debugging
    const tierCounts = getTierCounts(searchResults);
    console.log(`[Text Search] Results by tier:`, tierCounts);
    console.log(`[Text Search] Search completed, found ${searchResults.length} results`);

    // Transform results to include match_tier and search_rank
    const clipsArray = searchResults.slice(0, limit).map((result) => ({
      ...result.item,
      match_tier: result.matchTier,
      search_rank: result.searchRank,
      segments: result.item.segments || [],
    }));

    /* AI Embedding Search - Temporarily disabled, keeping for future use
    console.log(`[AI Search] Generating embedding for query: "${query}"`);
    const embeddingResult = await generateEmbedding(query);

    if (embeddingResult.error || !embeddingResult.data) {
      console.error(
        "[AI Search] Failed to generate embedding:",
        embeddingResult.error
      );
      // Use text search as fallback
      // ... fallback code ...
    }

    // Perform vector similarity search using the generated embedding
    console.log(
      `[AI Search] Embedding generated successfully, dimensions: ${embeddingResult.data.embedding.length}`
    );

    const embeddingText = `[${embeddingResult.data.embedding.join(",")}]`;
    const cutoff = 0.2;

    const { data: clips, error } = await supabase.rpc(
      "search_user_clips_by_vector",
      {
        query_embedding_text: embeddingText,
        target_user_id: teamId ? undefined : user.id,
        match_limit: limit,
        match_threshold: cutoff,
        target_team_id: teamId || undefined,
      }
    );
    */

    // Data is already in the correct nested structure from Supabase
    // No transformation needed - clipsArray already has parliament_member_clips nested
    return NextResponse.json({
      success: true,
      clips: clipsArray,
      query,
      searchType: "three_tier_text",
      tierCounts,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("User clips search error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message:
      "POST to this endpoint with { query, limit?, teamId? } to search user clips using 3-tier text search (exact phrase → all words → any word)",
    method: "POST",
    endpoint: "/api/user-clips/search",
  });
}
