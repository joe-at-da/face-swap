import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import {
  isLiberalDemocratCached,
  getLDMemberIds,
} from "@/lib/liberal-democrat-helpers";
import { handleError } from "@/lib/getErrorMessage";
import {
  resolveMemberIds,
  performClipSearch,
} from "@/lib/clips/search-helpers";

// partyNames intentionally omitted — LD clips are always scoped to Liberal Democrats
const searchLdSchema = z.object({
  query: z.string().max(500).optional(),
  memberIds: z.array(z.number().int().positive()).max(100).optional(),
  teamId: z.string().uuid().optional(),
  dateFrom: z.string().optional(),
  dateTo: z.string().optional(),
  searchType: z.enum(["hybrid", "text"]).default("hybrid"),
  limit: z.number().int().min(1).max(100).default(24),
  offset: z.number().int().min(0).default(0),
});

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

    const parsed = searchLdSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: "Invalid request parameters" },
        { status: 400 }
      );
    }

    const { query, memberIds, teamId, dateFrom, dateTo, searchType, limit, offset } = parsed.data;

    // IDOR protection: verify team membership when teamId is provided
    if (teamId) {
      const { data: isMember, error: memberError } =
        await supabaseAdminClient.rpc("is_team_member", {
          p_team_id: teamId,
          p_user_id: user.id,
        });

      if (memberError || !isMember) {
        return NextResponse.json(
          { error: "You are not a member of this team" },
          { status: 403 }
        );
      }
    }

    // Check LD access (personal or team context)
    const isLD = await isLiberalDemocratCached(user.id, teamId, supabaseAdminClient);
    if (!isLD) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    // Use admin client for data queries — longer statement_timeout than PostgREST default (8s)
    const db = supabaseAdminClient;

    // Always scope to LD members
    const ldMemberIds = await getLDMemberIds(db);
    if (ldMemberIds.length === 0) {
      return NextResponse.json({
        clips: [],
        total: 0,
        truncated: false,
        query: query?.trim() || null,
        searchType: query?.trim() ? searchType : "browse",
        offset,
        limit,
      });
    }

    // Resolve user-provided member filters and intersect with LD members
    const userMemberFilter = await resolveMemberIds(db, memberIds, undefined);
    let targetMemberIds: number[];

    if (userMemberFilter !== null) {
      const ldSet = new Set(ldMemberIds);
      targetMemberIds = userMemberFilter.filter((id) => ldSet.has(id));
    } else {
      targetMemberIds = ldMemberIds;
    }

    // Empty intersection: user's member filter has no LD members
    if (targetMemberIds.length === 0) {
      return NextResponse.json({
        clips: [],
        total: 0,
        truncated: false,
        query: query?.trim() || null,
        searchType: query?.trim() ? searchType : "browse",
        offset,
        limit,
      });
    }

    const result = await performClipSearch({
      db,
      userId: user.id,
      targetMemberIds,
      query,
      dateFrom,
      dateTo,
      searchType,
      limit,
      offset,
      trackingScope: "ld_parliament_clips",
      trackingPrefix: "ld",
      hasFilters: userMemberFilter !== null,
      endpoint: "/api/clips/search-ld",
    });

    if (!result.ok) {
      return NextResponse.json(
        { error: result.error },
        { status: result.status }
      );
    }

    return NextResponse.json(result.data);
  } catch (error) {
    handleError(error, {
      component: "api",
      action: "POST /api/clips/search-ld",
      feature: "ld-clips",
    });
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
