import type { Database } from "@/supabaseTypes";
import type { TestSupabaseAdmin } from "../supabase-admin";
import { E2E_MEMBER_ID_START } from "../constants";

type Tables = Database["public"]["Tables"];
type ParliamentMemberInsert = Tables["parliament_members"]["Insert"];
type ParliamentMemberRow = Tables["parliament_members"]["Row"];
type ParliamentMemberContactInsert =
  Tables["parliament_member_contacts"]["Insert"];
type ParliamentMemberContactRow = Tables["parliament_member_contacts"]["Row"];
type ParliamentMemberPortraitInsert =
  Tables["parliament_member_portraits"]["Insert"];
type ParliamentMemberPortraitRow =
  Tables["parliament_member_portraits"]["Row"];
type ParliamentEventInsert = Tables["parliament_events"]["Insert"];
type ParliamentEventRow = Tables["parliament_events"]["Row"];

type CreateParliamentMemberOpts = Partial<
  Omit<ParliamentMemberInsert, "member_id">
> & { member_id?: number };

export async function createTestParliamentMember(
  admin: TestSupabaseAdmin,
  opts: CreateParliamentMemberOpts & { member_id: number }
): Promise<ParliamentMemberRow> {
  const defaults = {
    display_name: `E2E Test Member ${opts.member_id}`,
    is_current_member: true,
    is_deleted: false,
    constituency_name: "Test Constituency",
    party_name: "Test Party",
    party_abbreviation: "TST",
    house_name: "Commons" as const,
  } satisfies Partial<ParliamentMemberInsert>;

  const { data, error } = await admin
    .from("parliament_members")
    .upsert({ ...defaults, ...opts }, { onConflict: "member_id" })
    .select()
    .single();

  if (error) throw new Error(`createTestParliamentMember: ${error.message}`);
  return data;
}

export async function createTestParliamentMemberContact(
  admin: TestSupabaseAdmin,
  opts: Pick<ParliamentMemberContactInsert, "member_id" | "email"> &
    Partial<Omit<ParliamentMemberContactInsert, "member_id" | "email">>
): Promise<ParliamentMemberContactRow> {
  const defaults = {
    is_deleted: false,
    is_primary: true,
  } satisfies Partial<ParliamentMemberContactInsert>;

  const { data, error } = await admin
    .from("parliament_member_contacts")
    .upsert({ ...defaults, ...opts })
    .select()
    .single();

  if (error)
    throw new Error(`createTestParliamentMemberContact: ${error.message}`);
  return data;
}

export async function createTestParliamentMemberPortrait(
  admin: TestSupabaseAdmin,
  opts: Pick<ParliamentMemberPortraitInsert, "member_id"> &
    Partial<Omit<ParliamentMemberPortraitInsert, "member_id">>
): Promise<ParliamentMemberPortraitRow> {
  const defaults = {
    image_url: "https://thempai-dev.lon1.digitaloceanspaces.com/speakerfaces/e2e-test/e2e-mp-portrait.png",
    crop_type: 0,
    is_primary: true,
    is_deleted: false,
    is_valid_mp_image: true,
    source: "parliament_api",
  } satisfies Partial<ParliamentMemberPortraitInsert>;

  const { data, error } = await admin
    .from("parliament_member_portraits")
    .upsert({ ...defaults, ...opts })
    .select()
    .single();

  if (error)
    throw new Error(`createTestParliamentMemberPortrait: ${error.message}`);
  return data;
}

export async function createTestParliamentEvent(
  admin: TestSupabaseAdmin,
  opts?: Partial<ParliamentEventInsert>
): Promise<ParliamentEventRow> {
  const now = new Date().toISOString();
  const defaults = {
    event_id: `e2e-event-${Date.now()}`,
    event_url: "https://example.com/e2e-test-event",
    title: "E2E Test Session",
    session_date: now.split("T")[0],
    status: "processed" as const,
    updated_at: now,
  } satisfies Partial<ParliamentEventInsert>;

  const { data, error } = await admin
    .from("parliament_events")
    .insert({ ...defaults, ...opts })
    .select()
    .single();

  if (error) throw new Error(`createTestParliamentEvent: ${error.message}`);
  return data;
}

/**
 * Clean up all test parliament data (member_id >= 90000).
 */
export async function cleanupTestParliamentData(
  admin: TestSupabaseAdmin
): Promise<void> {
  // Step 1: Delete child records in parallel (no FK deps between them)
  await Promise.all([
    admin.from("parliament_member_clips").delete().gte("member_id", E2E_MEMBER_ID_START),
    admin.from("parliament_member_contacts").delete().gte("member_id", E2E_MEMBER_ID_START),
    admin.from("parliament_member_portraits").delete().gte("member_id", E2E_MEMBER_ID_START),
  ]);
  // Step 2: Delete parent records in parallel
  await Promise.all([
    admin.from("parliament_members").delete().gte("member_id", E2E_MEMBER_ID_START),
    admin.from("parliament_events").delete().like("event_id", "e2e-%"),
  ]);
}
