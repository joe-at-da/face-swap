import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { isAdminCached } from "@/lib/admin-helpers";
import { handleError } from "@/lib/getErrorMessage";
import {
  resolveMemberIds,
  performClipSearch,
} from "@/lib/clips/search-helpers";

const searchAllSchema = z.object({
  query: z.string().max(500).optional(),
  memberIds: z.array(z.number().int().positive()).max(100).optional(),
  partyNames: z.array(z.string().max(200)).max(20).optional(),
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

    const isAdmin = await isAdminCached(user.id, supabaseAdminClient);
    if (!isAdmin) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
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

    const parsed = searchAllSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: "Invalid request parameters" },
        { status: 400 }
      );
    }

    const { query, memberIds, partyNames, dateFrom, dateTo, searchType, limit, offset } = parsed.data;
    // Use admin client for all data queries — longer statement_timeout than PostgREST default (8s)
    const db = supabaseAdminClient;
    const resolvedMemberIds = await resolveMemberIds(db, memberIds, partyNames);

    // Empty intersection: filters active but no matching members → zero results
    if (resolvedMemberIds !== null && resolvedMemberIds.length === 0) {
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
      targetMemberIds: resolvedMemberIds,
      query,
      dateFrom,
      dateTo,
      searchType,
      limit,
      offset,
      trackingScope: "all_parliament_clips",
      trackingPrefix: "admin",
      hasFilters: resolvedMemberIds !== null,
      endpoint: "/api/clips/search-all",
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
      action: "POST /api/clips/search-all",
      feature: "all-clips",
    });
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
