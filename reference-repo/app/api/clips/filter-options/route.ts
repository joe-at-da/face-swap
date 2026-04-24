import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { isAdminCached, deduplicateParties } from "@/lib/admin-helpers";
import { handleError } from "@/lib/getErrorMessage";

function escapeLikePattern(input: string): string {
  return input.replace(/[%_\\]/g, "\\$&");
}

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

    const isAdmin = await isAdminCached(user.id, supabaseAdminClient);
    if (!isAdmin) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const type = searchParams.get("type");

    if (type === "parties") {
      const { data: members, error } = await supabase
        .from("parliament_members")
        .select("party_name, party_abbreviation, party_background_colour, party_foreground_colour")
        .eq("is_current_member", true)
        .eq("is_deleted", false)
        .not("party_name", "is", null)
        .order("party_name");

      if (error) throw error;

      return NextResponse.json({ parties: deduplicateParties(members || []) });
    }

    if (type === "mps") {
      const partyParam = searchParams.get("party");
      const search = searchParams.get("search") || "";

      let query = supabase
        .from("parliament_members")
        .select(`
          member_id,
          display_name,
          party_abbreviation,
          party_name,
          party_background_colour,
          party_foreground_colour,
          parliament_member_portraits (
            image_url
          )
        `)
        .eq("is_current_member", true)
        .eq("is_deleted", false)
        .eq("parliament_member_portraits.is_deleted", false)
        .eq("parliament_member_portraits.is_primary", true)
        .order("display_name");

      if (partyParam) {
        const partyNames = partyParam.split(",").map((p) => p.trim());
        query = query.in("party_name", partyNames);
      }

      if (search) {
        query = query.ilike("display_name", `%${escapeLikePattern(search.slice(0, 100))}%`);
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
          (mp.parliament_member_portraits as Array<{ image_url: string }> | null)?.[0]
            ?.image_url || null,
      }));

      return NextResponse.json({ mps: formatted });
    }

    return NextResponse.json(
      { error: "Invalid type parameter. Use 'parties' or 'mps'." },
      { status: 400 }
    );
  } catch (error) {
    const message = handleError(error, {
      component: "api",
      action: "GET /api/clips/filter-options",
      feature: "all-clips",
    });
    return NextResponse.json(
      { error: message || "Internal server error" },
      { status: 500 }
    );
  }
}
