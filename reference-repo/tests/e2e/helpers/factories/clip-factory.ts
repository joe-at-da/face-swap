import type { Database } from "@/supabaseTypes";
import type { TestSupabaseAdmin } from "../supabase-admin";


type Tables = Database["public"]["Tables"];
type ParliamentMemberClipInsert =
  Tables["parliament_member_clips"]["Insert"];
type ParliamentMemberClipRow = Tables["parliament_member_clips"]["Row"];
type UserClipInsert = Tables["user_clips"]["Insert"];
type UserClipRow = Tables["user_clips"]["Row"];

type CreateParliamentMemberClipOpts = Pick<
  ParliamentMemberClipInsert,
  "member_id"
> &
  Partial<Omit<ParliamentMemberClipInsert, "member_id">>;

export async function createTestParliamentMemberClip(
  admin: TestSupabaseAdmin,
  opts: CreateParliamentMemberClipOpts
): Promise<ParliamentMemberClipRow> {
  const now = new Date().toISOString();
  const defaults = {
    full_video_path: "https://thempai.lon1.digitaloceanspaces.com/parliament-clips/e2e-test/e2e-video.mp4",
    start_timestamp: now,
    end_timestamp: now,
    transcript: "E2E test transcript content for testing purposes.",
    clip_url: "https://thempai.lon1.digitaloceanspaces.com/parliament-clips/e2e-test/e2e-clip.mp4",
    thumbnail_url: "https://thempai-dev.lon1.digitaloceanspaces.com/speakerfaces/e2e-test/e2e-thumbnail.png",
    status: "completed" as const,
    is_deleted: false,
    is_false_positive: false,
    is_unidentified: false,
    duration_seconds: 30,
    description: "E2E test clip description",
    session_date: now.split("T")[0],
  } satisfies Partial<ParliamentMemberClipInsert>;

  const { data, error } = await admin
    .from("parliament_member_clips")
    .insert({ ...defaults, ...opts })
    .select()
    .single();

  if (error)
    throw new Error(`createTestParliamentMemberClip: ${error.message}`);
  return data;
}

type CreateUserClipOpts = Pick<UserClipInsert, "user_id" | "clip_id"> &
  Partial<Omit<UserClipInsert, "user_id" | "clip_id">>;

export async function createTestUserClip(
  admin: TestSupabaseAdmin,
  opts: CreateUserClipOpts
): Promise<UserClipRow> {
  const defaults = {
    title: `E2E Test User Clip ${Date.now()}`,
    description: "E2E test user clip description",
    clip_url: "https://thempai.lon1.digitaloceanspaces.com/parliament-clips/e2e-test/e2e-user-clip.mp4",
    vertical_clip_url: "https://thempai.lon1.digitaloceanspaces.com/parliament-clips/e2e-test/e2e-user-clip-vertical.mp4",
    thumbnail_url: "https://thempai-dev.lon1.digitaloceanspaces.com/speakerfaces/e2e-test/e2e-user-thumbnail.png",
    vertical_thumbnail_url: "https://thempai-dev.lon1.digitaloceanspaces.com/speakerfaces/e2e-test/e2e-user-vertical-thumbnail.png",
    transcript: "E2E test transcript for user clip.",
    status: "completed" as const,
    is_deleted: false,
    duration: "00:00:30",
    clip_duration_seconds: 30,
  } satisfies Partial<UserClipInsert>;

  const { data, error } = await admin
    .from("user_clips")
    .insert({ ...defaults, ...opts })
    .select()
    .single();

  if (error) throw new Error(`createTestUserClip: ${error.message}`);
  return data;
}
