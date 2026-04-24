"use server";
import "server-only";

import { getErrorMessage } from "@/lib/getErrorMessage";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

export async function getUserFollowedMemebers(userId: string) {
  try {
    const { data: userTeamMembers, error: userTeamMembersError } =
      await supabaseAdminClient
        .from("team_members")
        .select("*")
        .eq("user_id", userId)
        .eq("role", "user");
    if (userTeamMembersError) {
      throw userTeamMembersError;
    }
    const teamIds = userTeamMembers?.map((member) => member.team_id) || [];
    const { data: teams, error: teamsError } = await supabaseAdminClient
      .from("teams")
      .select("owner_id")
      .in("id", teamIds)
      .eq("is_deleted", false);

    if (teamsError) {
      throw teamsError;
    }
    const teamOwnerIds = teams?.map((team) => team.owner_id) || [];
    teamOwnerIds.push(userId);

    const { data: teamOwnerMembers, error: teamOwnerMembersError } =
      await supabaseAdminClient
        .from("user_roles")
        .select("member_id")
        .in("user_id", teamOwnerIds);

    if (teamOwnerMembersError) {
      throw teamOwnerMembersError;
    }

    const followedMps = teamOwnerMembers?.map((mp) => mp.member_id) || [];
    return {
      data: Array.from(new Set(followedMps)),
      error: null,
    };
  } catch (error: unknown) {
    const message = getErrorMessage(error);
    console.error("error in getUserFollowedMemebers: ", message);
    return {
      error: message,
      data: null,
    };
  }
}
