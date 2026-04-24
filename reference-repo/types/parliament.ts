import type { Tables } from "@/supabaseTypes";

/**
 * Parliament member clip type from database
 */
export type ParliamentMemberClip = Tables<"parliament_member_clips"> & {
  parliament_event?: {
    session_date: string | null;
    title: string | null;
  } | null;
};

/**
 * Parliament member type with portraits relationship
 * This represents a subset of parliament_members fields commonly used in components
 */
export type ParliamentMember = {
  display_name: string | null;
  party_abbreviation: string | null;
  party_name: string | null;
  constituency_name: string | null;
  parliament_member_portraits: Array<{
    image_url: string;
    is_primary: boolean | null;
  }> | null;
};

/**
 * Full parliament member type from database
 */
export type ParliamentMemberFull = Tables<"parliament_members">;

/**
 * Clip enriched with MP info for the all-clips admin view
 */
export type AllClipWithMP = ParliamentMemberClip & {
  mp_display_name: string | null;
  mp_portrait_url: string | null;
  mp_party_abbreviation: string | null;
  mp_party_name: string | null;
  mp_party_background_colour: string | null;
  mp_party_foreground_colour: string | null;
};

export type PartyOption = {
  party_name: string;
  party_abbreviation: string;
  party_background_colour: string | null;
  party_foreground_colour: string | null;
};

export type MPOption = {
  member_id: number;
  display_name: string;
  party_abbreviation: string | null;
  party_name: string | null;
  party_background_colour: string | null;
  party_foreground_colour: string | null;
  portrait_url: string | null;
};
