import { Tables } from "@/supabaseTypes";

// Base types from Supabase
type ParliamentMemberClip = Tables<"parliament_member_clips">;
type ParliamentMember = Tables<"parliament_members">;

/**
 * Session clip with joined member data
 * Used in video editor components to represent clips from a parliament session
 */
export type SessionClipWithMember = Pick<
  ParliamentMemberClip,
  | "id"
  | "member_id"
  | "thumbnail_url"
  | "vertical_thumbnail_url"
  | "start_timestamp"
  | "end_timestamp"
  | "transcript"
  | "description"
  | "session_uid"
> & {
  parliament_members: Pick<ParliamentMember, "display_name"> | null;
};

/**
 * Full main clip data with complete member information
 * Used for the primary clip the user selected to edit
 */
export type MainClipWithFullMember = ParliamentMemberClip & {
  parliament_members: Pick<
    ParliamentMember,
    | "member_id"
    | "display_name"
    | "full_title"
    | "given_name"
    | "family_name"
    | "party_name"
    | "party_abbreviation"
    | "party_background_colour"
    | "party_foreground_colour"
    | "constituency_name"
    | "house_name"
    | "gender"
    | "is_current_member"
  >;
};

/**
 * Timeline item representing a clip added to the video editor timeline
 */
export type TimelineItem = {
  /** Unique identifier for this timeline item */
  id: string;
  /** Original clip ID from parliament_member_clips */
  clipId: string;
  /** Track index (0-based, represents the row in the timeline) */
  trackIndex: number;
  /** Start time in seconds (relative to timeline start) */
  startTime: number;
  /** End time in seconds (relative to timeline start) */
  endTime: number;
  /** Duration in seconds */
  duration: number;
  /** Original clip start timestamp from database (stored as MM:SS.mmm, displayed as hh:mm:ss.yyy) */
  originalStartTimestamp: string;
  /** Original clip end timestamp from database (stored as MM:SS.mmm, displayed as hh:mm:ss.yyy) */
  originalEndTimestamp: string;
  /** Current (possibly trimmed) start timestamp (hh:mm:ss.yyy format) */
  currentStartTimestamp: string;
  /** Current (possibly trimmed) end timestamp (hh:mm:ss.yyy format) */
  currentEndTimestamp: string;
  /** Whether this item is muted */
  isMuted: boolean;
  /** Thumbnail URL for preview */
  thumbnailUrl: string | null;
  /** MP name for display */
  mpName: string;
  /** Transcript text */
  transcript: string;
};

/**
 * Timeline track representing a horizontal row in the timeline
 */
export type TimelineTrack = {
  /** Track ID */
  id: string;
  /** Track index (0-based) */
  index: number;
  /** Items in this track */
  items: TimelineItem[];
};
