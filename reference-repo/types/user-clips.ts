import type { Tables } from "@/supabaseTypes";

/**
 * User clip from database
 */
export type UserClipRow = Tables<"user_clips">;

/**
 * User clip with parliament member information
 * This represents the common shape used across the application
 */
export interface UserClip {
  id: string;
  created_at: string;
  updated_at: string;
  status: string;
  duration: string | null;
  title: string | null;
  description: string | null;
  segments: Array<{
    start_timestamp: string;
    end_timestamp: string;
  }>;
  transcript: string | null;
  transcript_manually_edited: boolean;
  clip_url: string | null;
  vertical_clip_url: string | null;
  thumbnail_url: string | null;
  vertical_thumbnail_url: string | null;
  watermark_url: string | null;
  watermark_position: string | null;
  error_message: string | null;
  parliament_member_clips: {
    id: string;
    member_id: number;
    session_date?: string | null;
    parliament_members: {
      display_name: string;
      party_name: string | null;
      party_abbreviation: string | null;
    };
  };
}

/**
 * Extended user clip data with additional details
 * Used in detail pages with more MP information
 */
export interface UserClipData {
  id: string;
  created_at: string;
  updated_at: string;
  status: string;
  duration: string | null;
  team_id: string | null;
  title: string | null;
  description: string | null;
  user_id: string;
  segments: Array<{
    start_timestamp: string;
    end_timestamp: string;
  }>;
  transcript: string | null;
  transcript_manually_edited: boolean;
  clip_url: string | null;
  vertical_clip_url: string | null;
  thumbnail_url: string | null;
  vertical_thumbnail_url: string | null;
  watermark_url: string | null;
  watermark_position: string | null;
  error_message: string | null;
  parliament_member_clips: {
    id: string;
    title?: string;
    parliament_members: {
      display_name: string;
      party_name: string | null;
      party_abbreviation: string | null;
      constituency_name: string | null;
      member_id?: number;
      profile_image?: string | null;
    };
  };
}

/**
 * Public clip data for unauthenticated views
 */
export interface PublicClipData {
  id: string;
  created_at: string;
  status: string;
  duration: string | null;
  transcript: string | null;
  transcript_manually_edited: boolean;
  title: string | null;
  description: string | null;
  clip_url: string | null;
  vertical_clip_url: string | null;
  thumbnail_url: string | null;
  vertical_thumbnail_url: string | null;
  parliament_event_title: string | null;
  parliament_event_session_date: string | null;
  parliament_member_clips?: {
    session_type: string | null;
    session_date: string | null;
    parliament_members: {
      member_id: number;
      display_name: string;
      full_title: string | null;
      party_name: string | null;
      party_abbreviation: string | null;
      party_background_colour: string | null;
      party_foreground_colour: string | null;
      constituency_name: string | null;
      profile_image: string | null;
    };
  };
}

/**
 * Pagination information for clip lists
 */
export interface PaginationInfo {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  itemsPerPage: number;
}
