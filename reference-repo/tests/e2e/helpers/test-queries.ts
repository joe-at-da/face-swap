import type { TestSupabaseAdmin } from "./supabase-admin";
import type { Database } from "@/supabaseTypes";

type ClipStatus = Database["public"]["Enums"]["parliament_clip_status"];

/** Get a parliament member clip ID for the given user email */
export async function getTestMpClipId(
  admin: TestSupabaseAdmin,
  email: string
): Promise<string | null> {
  const { data: userRole } = await admin
    .from("user_roles")
    .select("member_id")
    .eq("email", email)
    .single();
  if (!userRole?.member_id) return null;

  const { data: clips } = await admin
    .from("parliament_member_clips")
    .select("id")
    .eq("member_id", userRole.member_id)
    .eq("is_deleted", false)
    .limit(1);
  return clips?.[0]?.id ?? null;
}

/** Get a user clip ID by status */
export async function getTestUserClipId(
  admin: TestSupabaseAdmin,
  userId: string,
  status: ClipStatus = "completed"
): Promise<string | null> {
  const { data: clips } = await admin
    .from("user_clips")
    .select("id")
    .eq("user_id", userId)
    .eq("status", status)
    .eq("is_deleted", false)
    .limit(1);
  return clips?.[0]?.id ?? null;
}
