import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { isLiberalDemocratCached } from "@/lib/liberal-democrat-helpers";
import LDClipsListView from "./components/ld-clips-list-view";

interface PageProps {
  searchParams: Promise<{ teamId?: string }>;
}

export default async function LDClipsPage({ searchParams }: PageProps) {
  const supabase = await createSupabaseServerClient();
  const { teamId } = await searchParams;

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // IDOR protection: verify team membership when teamId is provided
  if (teamId) {
    const { data: isMember, error: memberError } =
      await supabaseAdminClient.rpc("is_team_member", {
        p_team_id: teamId,
        p_user_id: user.id,
      });

    if (memberError || !isMember) {
      redirect("/dashboard");
    }
  }

  const isLD = await isLiberalDemocratCached(
    user.id,
    teamId,
    supabaseAdminClient
  );
  if (!isLD) {
    redirect("/dashboard");
  }

  return <LDClipsListView teamId={teamId} />;
}
