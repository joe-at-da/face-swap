import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import {
  isLiberalDemocratCached,
  getLDMemberIds,
} from "@/lib/liberal-democrat-helpers";
import { handleError } from "@/lib/getErrorMessage";

function escapeLikePattern(input: string): string {
  return input.replace(/[%_\\]/g, "\\$&");
}

/**
 * LD-scoped version of /api/clips/filter-options.
 * Requires LD access (personal or team) instead of admin.
 * Only returns MPs belonging to the Liberal Democrats party.
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const teamId = searchParams.get("teamId") || undefined;

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
    const isLD = await isLiberalDemocratCached(
      user.id,
      teamId,
      supabaseAdminClient
    );
    if (!isLD) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    const type = searchParams.get("type");

    if (type === "mps") {
      const search = searchParams.get("search") || "";

      // Get LD member IDs to scope results
      const ldMemberIds = await getLDMemberIds(supabaseAdminClient);
      if (ldMemberIds.length === 0) {
        return NextResponse.json({ mps: [] });
      }

      let query = supabaseAdminClient
        .from("parliament_members")
        .select(
          `
          member_id,
          display_name,
          party_abbreviation,
          party_name,
          party_background_colour,
          party_foreground_colour,
          parliament_member_portraits (
            image_url
          )
        `
        )
        .in("member_id", ldMemberIds)
        .eq("is_current_member", true)
        .eq("is_deleted", false)
        .eq("parliament_member_portraits.is_deleted", false)
        .eq("parliament_member_portraits.is_primary", true)
        .order("display_name");

      if (search) {
        query = query.ilike(
          "display_name",
          `%${escapeLikePattern(search.slice(0, 100))}%`
        );
      }

      const { data: mps, error } = await query.limit(50);
      if (error) throw error;

      const formatted = (mps || []).map((mp) => ({
        member_id: mp.member_id,
        display_name: mp.display_name,
        party_abbreviation: mp.party_abbreviation,
        party_name: mp.party_name,
        party_background_colour: mp.party_background_colour,
        party_foreground_colour: mp.party_foreground_colour,
        portrait_url:
          (
            mp.parliament_member_portraits as Array<{
              image_url: string;
            }> | null
          )?.[0]?.image_url || null,
      }));

      return NextResponse.json({ mps: formatted });
    }

    return NextResponse.json(
      { error: "Invalid type parameter. Use 'mps'." },
      { status: 400 }
    );
  } catch (error) {
    const message = handleError(error, {
      component: "api",
      action: "GET /api/clips/ld-filter-options",
      feature: "ld-clips",
    });
    return NextResponse.json(
      { error: message || "Internal server error" },
      { status: 500 }
    );
  }
}
