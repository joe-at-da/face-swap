import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { isAdminCached } from "@/lib/admin-helpers";
import { resolveEffectiveMemberId } from "@/lib/resolve-team-member-id";
import { captureServerEvent } from "@/lib/posthog-server";
import { generateAndFormatEmbedding } from "@/services/ai/embedding-service";
import { rerankClips } from "@/services/ai/reranking-service";
import { handleError } from "@/lib/getErrorMessage";
import { ErrorLogger } from "@/lib/errorLogger";
import { enrichWithParliamentEvents } from "@/lib/clips/enrich";
import {
  CLIPS_SELECT_COLUMNS,
  escapePostgrestFilterValue,
  filterByDate,
  type SupabaseInstance,
} from "@/lib/clips/search-helpers";

const searchSchema = z.object({
  query: z.string().max(500).optional(),
  memberId: z.number().int().positive(),
  dateFrom: z.string().optional(),
  dateTo: z.string().optional(),
  searchType: z.enum(["hybrid", "text"]).default("hybrid"),
  limit: z.number().int().min(1).max(100).default(12),
  offset: z.number().int().min(0).default(0),
  teamId: z.string().uuid().optional(),
});

async function performTextSearch(
  supabase: SupabaseInstance,
  query: string,
  memberId: number,
  limit: number,
  offset: number
) {
  // Use PostgreSQL websearch full-text search which leverages GIN indexes
  const { data: clips, count, error } = await supabase
    .from("parliament_member_clips")
    .select(CLIPS_SELECT_COLUMNS, { count: "exact" })
    .eq("member_id", memberId)
    .eq("is_deleted", false)
    .not("transcript", "is", null)
    .neq("transcript", "")
    .or(`transcript.wfts."${escapePostgrestFilterValue(query)}",description.wfts."${escapePostgrestFilterValue(query)}"`)
    .order("created_at", { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(`Text search failed: ${error.message}`);
  }

  return { clips: clips || [], total: count || 0 };
}

async function performTextSearchWithDateFilter(
  supabase: SupabaseInstance,
  query: string,
  memberId: number
) {
  // When date filters are active, fetch a larger set for in-memory date filtering
  // Still use PostgreSQL full-text search instead of loading all clips
  const { data: clips, error } = await supabase
    .from("parliament_member_clips")
    .select(CLIPS_SELECT_COLUMNS)
    .eq("member_id", memberId)
    .eq("is_deleted", false)
    .not("transcript", "is", null)
    .neq("transcript", "")
    .or(`transcript.wfts."${escapePostgrestFilterValue(query)}",description.wfts."${escapePostgrestFilterValue(query)}"`)
    .order("created_at", { ascending: false })
    .limit(1000);

  if (error) {
    throw new Error(`Text search failed: ${error.message}`);
  }

  return clips || [];
}

async function performHybridSearch(
  supabase: SupabaseInstance,
  query: string,
  memberId: number
): Promise<{ clips: Record<string, unknown>[] } | { error: string }> {
  const trimmedQuery = query.trim();
  const startTotal = Date.now();

  const startEmbed = Date.now();
  const embeddingResult = await generateAndFormatEmbedding(trimmedQuery);
  console.log(`[search] Embedding: ${Date.now() - startEmbed}ms`);

  if (embeddingResult.error || !embeddingResult.data) {
    console.error("[search] Embedding failed for query:", trimmedQuery, "error:", embeddingResult.error);
    return { error: `Embedding generation failed: ${embeddingResult.error}` };
  }

  const RETRIEVAL_COUNT = 200;
  const startRpc = Date.now();
  const { data: hybridResults, error: searchError } = await supabase.rpc(
    "hybrid_search_parliament_clips",
    {
      query_embedding_text: embeddingResult.data,
      fulltext_query: trimmedQuery,
      target_member_id: memberId,
      match_count: RETRIEVAL_COUNT,
    }
  );
  console.log(`[search] RPC: ${Date.now() - startRpc}ms (${hybridResults?.length ?? 0} results)`);

  if (searchError) {
    console.error("[search] RPC hybrid_search_parliament_clips failed:", searchError.message, searchError.code, searchError.details);
    return { error: `RPC error: ${searchError.message}` };
  }

  let finalClips = hybridResults || [];

  if (finalClips.length > 1) {
    const startRerank = Date.now();
    const rerankResult = await rerankClips(trimmedQuery, finalClips);
    console.log(`[search] Rerank: ${Date.now() - startRerank}ms`);
    if (rerankResult.data) {
      finalClips = rerankResult.data;
    }
  }

  console.log(`[search] Hybrid total: ${Date.now() - startTotal}ms`);
  return { clips: finalClips };
}

export async function POST(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON body" },
        { status: 400 }
      );
    }

    const parsed = searchSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: "Invalid request parameters" },
        { status: 400 }
      );
    }

    const { query, memberId, dateFrom, dateTo, searchType, limit, offset, teamId } = parsed.data;

    // Authorization: non-admin users can only search their own member's clips
    const isAdmin = await isAdminCached(user.id, supabaseAdminClient);
    if (!isAdmin) {
      // Verify team membership when teamId is provided
      if (teamId) {
        const { data: isMember } = await supabaseAdminClient.rpc(
          "is_team_member",
          { p_team_id: teamId, p_user_id: user.id }
        );
        if (!isMember) {
          return NextResponse.json({ error: "Forbidden" }, { status: 403 });
        }
      }

      const effectiveMemberId = await resolveEffectiveMemberId(
        user.id,
        teamId,
        supabaseAdminClient
      );
      if (memberId !== effectiveMemberId) {
        return NextResponse.json({ error: "Forbidden" }, { status: 403 });
      }
    }

    // Browse mode (no query)
    if (!query || !query.trim()) {
      const hasDateFilter = dateFrom || dateTo;

      if (!hasDateFilter) {
        // No date filter — efficient DB-level pagination
        const { data: clips, count, error } = await supabase
          .from("parliament_member_clips")
          .select(CLIPS_SELECT_COLUMNS, { count: "exact" })
          .eq("member_id", memberId)
          .eq("is_deleted", false)
          .not("transcript", "is", null)
          .neq("transcript", "")
          .order("created_at", { ascending: false })
          .range(offset, offset + limit - 1);

        if (error) throw error;

        const enrichedClips = await enrichWithParliamentEvents(clips || [], supabase);

        try {
          await captureServerEvent(user.id, "browse_performed", {
            member_id: memberId,
            results_count: count || 0,
            search_scope: "parliament_clips",
          });
        } catch {
          // PostHog tracking failure is non-critical
        }

        return NextResponse.json({
          clips: enrichedClips,
          total: count || 0,
          query: null,
          searchType: "browse",
          offset,
          limit,
        });
      }

      // Date filter active — fetch all for member, enrich, then filter
      const { data: clips, error } = await supabase
        .from("parliament_member_clips")
        .select(CLIPS_SELECT_COLUMNS)
        .eq("member_id", memberId)
        .eq("is_deleted", false)
        .not("transcript", "is", null)
        .neq("transcript", "")
        .order("created_at", { ascending: false });

      if (error) throw error;

      const enrichedClips = await enrichWithParliamentEvents(clips || [], supabase);
      const dateFiltered = filterByDate(enrichedClips, dateFrom, dateTo);
      const total = dateFiltered.length;
      const paged = dateFiltered.slice(offset, offset + limit);

      return NextResponse.json({
        clips: paged,
        total,
        query: null,
        searchType: "browse",
        offset,
        limit,
      });
    }

    const trimmedQuery = query.trim();

    // Text search
    if (searchType === "text") {
      const hasDateFilter = dateFrom || dateTo;

      if (!hasDateFilter) {
        // No date filter — use DB-level pagination with full-text search
        const { clips: searchClips, total } = await performTextSearch(
          supabase,
          trimmedQuery,
          memberId,
          limit,
          offset
        );

        const enrichedClips = await enrichWithParliamentEvents(searchClips, supabase);

        try {
          await captureServerEvent(user.id, "search_performed", {
            query: trimmedQuery,
            member_id: memberId,
            results_count: total,
            search_type: "fulltext",
            search_scope: "parliament_clips",
          });
        } catch {
          // PostHog tracking failure is non-critical
        }

        return NextResponse.json({
          clips: enrichedClips,
          total,
          query: trimmedQuery,
          searchType: "text",
          offset,
          limit,
        });
      }

      // Date filter active — fetch larger set, enrich, then filter
      const searchClips = await performTextSearchWithDateFilter(
        supabase,
        trimmedQuery,
        memberId
      );

      const enrichedAll = await enrichWithParliamentEvents(searchClips, supabase);
      const dateFiltered = filterByDate(enrichedAll, dateFrom, dateTo);
      const total = dateFiltered.length;
      const paged = dateFiltered.slice(offset, offset + limit);

      try {
        await captureServerEvent(user.id, "search_performed", {
          query: trimmedQuery,
          member_id: memberId,
          results_count: total,
          search_type: "fulltext",
          search_scope: "parliament_clips",
        });
      } catch {
        // PostHog tracking failure is non-critical
      }

      return NextResponse.json({
        clips: paged,
        total,
        query: trimmedQuery,
        searchType: "text",
        offset,
        limit,
      });
    }

    // Hybrid search
    const hybridResult = await performHybridSearch(
      supabase,
      trimmedQuery,
      memberId
    );

    if ("error" in hybridResult) {
      ErrorLogger.logApiError(
        new Error(hybridResult.error),
        "/api/clips/search",
        "POST",
        user.id
      );
      return NextResponse.json(
        { error: "AI search is currently unavailable. Please try text search." },
        { status: 503 }
      );
    }

    const startEnrich = Date.now();
    const enrichedAll = await enrichWithParliamentEvents(hybridResult.clips, supabase);
    console.log(`[search] Enrich: ${Date.now() - startEnrich}ms`);
    const dateFiltered = filterByDate(enrichedAll, dateFrom, dateTo);
    const total = dateFiltered.length;
    const paged = dateFiltered.slice(offset, offset + limit);

    try {
      await captureServerEvent(user.id, "search_performed", {
        query: trimmedQuery,
        member_id: memberId,
        results_count: total,
        search_type: "hybrid",
        search_scope: "parliament_clips",
      });
    } catch {
      // PostHog tracking failure is non-critical
    }

    return NextResponse.json({
      clips: paged,
      total,
      query: trimmedQuery,
      searchType: "hybrid",
      offset,
      limit,
    });
  } catch (error) {
    handleError(error, {
      component: "api",
      action: "POST /api/clips/search",
      feature: "search",
    });
    console.error("Clips search error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message:
      "POST to this endpoint with { memberId, query?, limit?, offset?, dateFrom?, dateTo?, searchType? } to browse/search clips.",
    method: "POST",
    endpoint: "/api/clips/search",
  });
}
