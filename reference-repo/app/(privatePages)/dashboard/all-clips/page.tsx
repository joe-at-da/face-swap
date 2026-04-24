import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { isAdminCached, deduplicateParties } from "@/lib/admin-helpers";
import AllClipsListView from "./components/all-clips-list-view";

export default async function AllClipsPage() {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  const isAdmin = await isAdminCached(user.id, supabaseAdminClient);
  if (!isAdmin) {
    redirect("/dashboard");
  }

  const { data: members } = await supabase
    .from("parliament_members")
    .select("party_name, party_abbreviation, party_background_colour, party_foreground_colour")
    .eq("is_current_member", true)
    .eq("is_deleted", false)
    .not("party_name", "is", null)
    .order("party_name");

  return <AllClipsListView initialParties={deduplicateParties(members || [])} />;
}
