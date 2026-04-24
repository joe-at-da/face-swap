export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      clip_notification_log: {
        Row: {
          clip_id: string
          id: string
          sent_at: string
          user_id: string
        }
        Insert: {
          clip_id: string
          id?: string
          sent_at?: string
          user_id: string
        }
        Update: {
          clip_id?: string
          id?: string
          sent_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "clip_notification_log_clip_id_fkey"
            columns: ["clip_id"]
            isOneToOne: false
            referencedRelation: "parliament_member_clips"
            referencedColumns: ["id"]
          },
        ]
      }
      public_clip_reports: {
        Row: {
          admin_notified_at: string | null
          clip_public_url: string
          clip_title_snapshot: string | null
          created_at: string
          details: string | null
          id: string
          notification_attempts: number
          notification_last_error: string | null
          notification_status: string
          reason: string
          reporter_fingerprint: string
          reporter_user_id: string | null
          review_notes: string | null
          review_status: string
          reviewed_at: string | null
          reviewed_by: string | null
          updated_at: string
          user_clip_id: string | null
        }
        Insert: {
          admin_notified_at?: string | null
          clip_public_url: string
          clip_title_snapshot?: string | null
          created_at?: string
          details?: string | null
          id?: string
          notification_attempts?: number
          notification_last_error?: string | null
          notification_status?: string
          reason: string
          reporter_fingerprint: string
          reporter_user_id?: string | null
          review_notes?: string | null
          review_status?: string
          reviewed_at?: string | null
          reviewed_by?: string | null
          updated_at?: string
          user_clip_id?: string | null
        }
        Update: {
          admin_notified_at?: string | null
          clip_public_url?: string
          clip_title_snapshot?: string | null
          created_at?: string
          details?: string | null
          id?: string
          notification_attempts?: number
          notification_last_error?: string | null
          notification_status?: string
          reason?: string
          reporter_fingerprint?: string
          reporter_user_id?: string | null
          review_notes?: string | null
          review_status?: string
          reviewed_at?: string | null
          reviewed_by?: string | null
          updated_at?: string
          user_clip_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "public_clip_reports_user_clip_id_fkey"
            columns: ["user_clip_id"]
            isOneToOne: false
            referencedRelation: "user_clips"
            referencedColumns: ["id"]
          },
        ]
      }
      event_processing_runs: {
        Row: {
          audio_path: string | null
          created_at: string | null
          event_id: string
          id: string
          processing_version: string | null
          results_url: string
          stats_asd_skipped_no_faces_selected: number | null
          stats_asd_skipped_no_quality_faces: number | null
          stats_asd_skipped_too_short: number | null
          stats_asd_total_segments: number | null
          stats_asd_with_faces: number | null
          stats_clip_horizontal_failed: number | null
          stats_clip_horizontal_ok: number | null
          stats_clip_segments_input: number | null
          stats_clip_segments_output: number | null
          stats_clip_thumbnails_failed: number | null
          stats_clip_thumbnails_ok: number | null
          stats_clip_uploads_failed: number | null
          stats_clip_uploads_successful: number | null
          stats_clip_vertical_failed: number | null
          stats_clip_vertical_ok: number | null
          stats_diarization_duration_seconds: number | null
          stats_diarization_num_segments: number | null
          stats_mp_id_avg_similarity: number | null
          stats_mp_id_identified: number | null
          stats_mp_id_identified_speakers: number | null
          stats_mp_id_similarity_count: number | null
          stats_mp_id_unidentified: number | null
          stats_mp_id_unidentified_speakers: number | null
          stats_mp_id_unique_speakers: number | null
          stats_transcription_avg_duration: number | null
          stats_transcription_empty: number | null
          stats_transcription_hallucination_filtered: number | null
          stats_transcription_total_duration: number | null
          stats_transcription_transcribed: number | null
          timing_asd_seconds: number | null
          timing_clip_creation_seconds: number | null
          timing_diarization_seconds: number | null
          timing_download_seconds: number | null
          timing_mp_identification_seconds: number | null
          timing_total_seconds: number | null
          timing_transcription_seconds: number | null
          video_path: string | null
        }
        Insert: {
          audio_path?: string | null
          created_at?: string | null
          event_id: string
          id?: string
          processing_version?: string | null
          results_url: string
          stats_asd_skipped_no_faces_selected?: number | null
          stats_asd_skipped_no_quality_faces?: number | null
          stats_asd_skipped_too_short?: number | null
          stats_asd_total_segments?: number | null
          stats_asd_with_faces?: number | null
          stats_clip_horizontal_failed?: number | null
          stats_clip_horizontal_ok?: number | null
          stats_clip_segments_input?: number | null
          stats_clip_segments_output?: number | null
          stats_clip_thumbnails_failed?: number | null
          stats_clip_thumbnails_ok?: number | null
          stats_clip_uploads_failed?: number | null
          stats_clip_uploads_successful?: number | null
          stats_clip_vertical_failed?: number | null
          stats_clip_vertical_ok?: number | null
          stats_diarization_duration_seconds?: number | null
          stats_diarization_num_segments?: number | null
          stats_mp_id_avg_similarity?: number | null
          stats_mp_id_identified?: number | null
          stats_mp_id_identified_speakers?: number | null
          stats_mp_id_similarity_count?: number | null
          stats_mp_id_unidentified?: number | null
          stats_mp_id_unidentified_speakers?: number | null
          stats_mp_id_unique_speakers?: number | null
          stats_transcription_avg_duration?: number | null
          stats_transcription_empty?: number | null
          stats_transcription_hallucination_filtered?: number | null
          stats_transcription_total_duration?: number | null
          stats_transcription_transcribed?: number | null
          timing_asd_seconds?: number | null
          timing_clip_creation_seconds?: number | null
          timing_diarization_seconds?: number | null
          timing_download_seconds?: number | null
          timing_mp_identification_seconds?: number | null
          timing_total_seconds?: number | null
          timing_transcription_seconds?: number | null
          video_path?: string | null
        }
        Update: {
          audio_path?: string | null
          created_at?: string | null
          event_id?: string
          id?: string
          processing_version?: string | null
          results_url?: string
          stats_asd_skipped_no_faces_selected?: number | null
          stats_asd_skipped_no_quality_faces?: number | null
          stats_asd_skipped_too_short?: number | null
          stats_asd_total_segments?: number | null
          stats_asd_with_faces?: number | null
          stats_clip_horizontal_failed?: number | null
          stats_clip_horizontal_ok?: number | null
          stats_clip_segments_input?: number | null
          stats_clip_segments_output?: number | null
          stats_clip_thumbnails_failed?: number | null
          stats_clip_thumbnails_ok?: number | null
          stats_clip_uploads_failed?: number | null
          stats_clip_uploads_successful?: number | null
          stats_clip_vertical_failed?: number | null
          stats_clip_vertical_ok?: number | null
          stats_diarization_duration_seconds?: number | null
          stats_diarization_num_segments?: number | null
          stats_mp_id_avg_similarity?: number | null
          stats_mp_id_identified?: number | null
          stats_mp_id_identified_speakers?: number | null
          stats_mp_id_similarity_count?: number | null
          stats_mp_id_unidentified?: number | null
          stats_mp_id_unidentified_speakers?: number | null
          stats_mp_id_unique_speakers?: number | null
          stats_transcription_avg_duration?: number | null
          stats_transcription_empty?: number | null
          stats_transcription_hallucination_filtered?: number | null
          stats_transcription_total_duration?: number | null
          stats_transcription_transcribed?: number | null
          timing_asd_seconds?: number | null
          timing_clip_creation_seconds?: number | null
          timing_diarization_seconds?: number | null
          timing_download_seconds?: number | null
          timing_mp_identification_seconds?: number | null
          timing_total_seconds?: number | null
          timing_transcription_seconds?: number | null
          video_path?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "fk_event_processing_runs_event_id"
            columns: ["event_id"]
            isOneToOne: false
            referencedRelation: "parliament_events"
            referencedColumns: ["event_id"]
          },
        ]
      }
      event_processing_segments: {
        Row: {
          asd_avg_speaking_score: number | null
          asd_best_face_size: number | null
          asd_best_is_frontal: boolean | null
          asd_best_occlusion_score: number | null
          asd_best_quality_score: number | null
          asd_chunked_decode: boolean | null
          asd_has_embedding: boolean | null
          asd_num_chunks: number | null
          asd_num_faces_saved: number | null
          asd_num_frames: number | null
          asd_num_tracks: number | null
          asd_selected_track_frames: number | null
          asd_skip_info: Json | null
          clip_url: string | null
          created_at: string | null
          duration_seconds: number | null
          end_seconds: number | null
          end_timestamp: string | null
          full_video_url: string | null
          id: string
          is_unidentified: boolean | null
          manually_assigned_at: string | null
          manually_assigned_by: string | null
          manually_assigned_member_id: number | null
          member_id: number | null
          merge_absorbed_count: number | null
          merge_absorbed_segments: Json | null
          merge_original_segments: Json | null
          merge_segment_count: number | null
          merge_was_merged: boolean | null
          mp_id_best_similarity: number | null
          mp_id_faces_with_embeddings: number | null
          mp_id_match_confidence: number | null
          mp_id_match_diagnostics: Json | null
          mp_id_matched_portrait_row_ids: Json | null
          mp_id_num_faces: number | null
          mp_id_num_matches: number | null
          mp_id_raw_vote_score: number | null
          mp_id_reason: string | null
          mp_id_similarity_tier: string | null
          mp_id_threshold_used: number | null
          mp_id_top_candidate_portrait_row_ids: Json | null
          mp_id_unique_mps_matched: number | null
          mp_id_weighted_vote_score: number | null
          processing_run_id: string
          segment_index: number
          speaker: string | null
          start_seconds: number | null
          start_timestamp: string | null
          thumbnail_url: string | null
          transcript: string | null
          transcription_avg_logprob: number | null
          transcription_compression_ratio: number | null
          transcription_duration: number | null
          transcription_language: string | null
          transcription_mode: string | null
          transcription_no_speech_prob: number | null
          transcription_raw_segments: Json | null
          transcription_temperature: Json | null
          transcription_token_count: number | null
          transcription_use_context: boolean | null
          vertical_clip_url: string | null
          vertical_thumbnail_url: string | null
        }
        Insert: {
          asd_avg_speaking_score?: number | null
          asd_best_face_size?: number | null
          asd_best_is_frontal?: boolean | null
          asd_best_occlusion_score?: number | null
          asd_best_quality_score?: number | null
          asd_chunked_decode?: boolean | null
          asd_has_embedding?: boolean | null
          asd_num_chunks?: number | null
          asd_num_faces_saved?: number | null
          asd_num_frames?: number | null
          asd_num_tracks?: number | null
          asd_selected_track_frames?: number | null
          asd_skip_info?: Json | null
          clip_url?: string | null
          created_at?: string | null
          duration_seconds?: number | null
          end_seconds?: number | null
          end_timestamp?: string | null
          full_video_url?: string | null
          id?: string
          is_unidentified?: boolean | null
          manually_assigned_at?: string | null
          manually_assigned_by?: string | null
          manually_assigned_member_id?: number | null
          member_id?: number | null
          merge_absorbed_count?: number | null
          merge_absorbed_segments?: Json | null
          merge_original_segments?: Json | null
          merge_segment_count?: number | null
          merge_was_merged?: boolean | null
          mp_id_best_similarity?: number | null
          mp_id_faces_with_embeddings?: number | null
          mp_id_match_confidence?: number | null
          mp_id_match_diagnostics?: Json | null
          mp_id_matched_portrait_row_ids?: Json | null
          mp_id_num_faces?: number | null
          mp_id_num_matches?: number | null
          mp_id_raw_vote_score?: number | null
          mp_id_reason?: string | null
          mp_id_similarity_tier?: string | null
          mp_id_threshold_used?: number | null
          mp_id_top_candidate_portrait_row_ids?: Json | null
          mp_id_unique_mps_matched?: number | null
          mp_id_weighted_vote_score?: number | null
          processing_run_id: string
          segment_index: number
          speaker?: string | null
          start_seconds?: number | null
          start_timestamp?: string | null
          thumbnail_url?: string | null
          transcript?: string | null
          transcription_avg_logprob?: number | null
          transcription_compression_ratio?: number | null
          transcription_duration?: number | null
          transcription_language?: string | null
          transcription_mode?: string | null
          transcription_no_speech_prob?: number | null
          transcription_raw_segments?: Json | null
          transcription_temperature?: Json | null
          transcription_token_count?: number | null
          transcription_use_context?: boolean | null
          vertical_clip_url?: string | null
          vertical_thumbnail_url?: string | null
        }
        Update: {
          asd_avg_speaking_score?: number | null
          asd_best_face_size?: number | null
          asd_best_is_frontal?: boolean | null
          asd_best_occlusion_score?: number | null
          asd_best_quality_score?: number | null
          asd_chunked_decode?: boolean | null
          asd_has_embedding?: boolean | null
          asd_num_chunks?: number | null
          asd_num_faces_saved?: number | null
          asd_num_frames?: number | null
          asd_num_tracks?: number | null
          asd_selected_track_frames?: number | null
          asd_skip_info?: Json | null
          clip_url?: string | null
          created_at?: string | null
          duration_seconds?: number | null
          end_seconds?: number | null
          end_timestamp?: string | null
          full_video_url?: string | null
          id?: string
          is_unidentified?: boolean | null
          manually_assigned_at?: string | null
          manually_assigned_by?: string | null
          manually_assigned_member_id?: number | null
          member_id?: number | null
          merge_absorbed_count?: number | null
          merge_absorbed_segments?: Json | null
          merge_original_segments?: Json | null
          merge_segment_count?: number | null
          merge_was_merged?: boolean | null
          mp_id_best_similarity?: number | null
          mp_id_faces_with_embeddings?: number | null
          mp_id_match_confidence?: number | null
          mp_id_match_diagnostics?: Json | null
          mp_id_matched_portrait_row_ids?: Json | null
          mp_id_num_faces?: number | null
          mp_id_num_matches?: number | null
          mp_id_raw_vote_score?: number | null
          mp_id_reason?: string | null
          mp_id_similarity_tier?: string | null
          mp_id_threshold_used?: number | null
          mp_id_top_candidate_portrait_row_ids?: Json | null
          mp_id_unique_mps_matched?: number | null
          mp_id_weighted_vote_score?: number | null
          processing_run_id?: string
          segment_index?: number
          speaker?: string | null
          start_seconds?: number | null
          start_timestamp?: string | null
          thumbnail_url?: string | null
          transcript?: string | null
          transcription_avg_logprob?: number | null
          transcription_compression_ratio?: number | null
          transcription_duration?: number | null
          transcription_language?: string | null
          transcription_mode?: string | null
          transcription_no_speech_prob?: number | null
          transcription_raw_segments?: Json | null
          transcription_temperature?: Json | null
          transcription_token_count?: number | null
          transcription_use_context?: boolean | null
          vertical_clip_url?: string | null
          vertical_thumbnail_url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "fk_segments_manually_assigned_member_id"
            columns: ["manually_assigned_member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
          {
            foreignKeyName: "fk_segments_member_id"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
          {
            foreignKeyName: "fk_segments_processing_run_id"
            columns: ["processing_run_id"]
            isOneToOne: false
            referencedRelation: "event_processing_runs"
            referencedColumns: ["id"]
          },
        ]
      }
      parliament_events: {
        Row: {
          author_name: string | null
          content_text: string | null
          content_type: string | null
          created_at: string | null
          deleted_at: string | null
          error_message: string | null
          event_id: string
          event_url: string
          has_ended: boolean | null
          id: string
          is_deleted: boolean
          is_live: boolean | null
          processing_completed_at: string | null
          processing_started_at: string | null
          retries_attempted: number | null
          session_date: string | null
          session_length_seconds: number | null
          session_start_time: string | null
          status: Database["public"]["Enums"]["parliament_event_processing_status"]
          title: string
          title_type: string | null
          updated_at: string
          updated_at_local: string | null
        }
        Insert: {
          author_name?: string | null
          content_text?: string | null
          content_type?: string | null
          created_at?: string | null
          deleted_at?: string | null
          error_message?: string | null
          event_id: string
          event_url: string
          has_ended?: boolean | null
          id?: string
          is_deleted?: boolean
          is_live?: boolean | null
          processing_completed_at?: string | null
          processing_started_at?: string | null
          retries_attempted?: number | null
          session_date?: string | null
          session_length_seconds?: number | null
          session_start_time?: string | null
          status?: Database["public"]["Enums"]["parliament_event_processing_status"]
          title: string
          title_type?: string | null
          updated_at: string
          updated_at_local?: string | null
        }
        Update: {
          author_name?: string | null
          content_text?: string | null
          content_type?: string | null
          created_at?: string | null
          deleted_at?: string | null
          error_message?: string | null
          event_id?: string
          event_url?: string
          has_ended?: boolean | null
          id?: string
          is_deleted?: boolean
          is_live?: boolean | null
          processing_completed_at?: string | null
          processing_started_at?: string | null
          retries_attempted?: number | null
          session_date?: string | null
          session_length_seconds?: number | null
          session_start_time?: string | null
          status?: Database["public"]["Enums"]["parliament_event_processing_status"]
          title?: string
          title_type?: string | null
          updated_at?: string
          updated_at_local?: string | null
        }
        Relationships: []
      }
      parliament_member_clips: {
        Row: {
          clip_url: string | null
          created_at: string | null
          deleted_at: string | null
          description: string | null
          description_embedding: string | null
          duration_seconds: number | null
          end_timestamp: string
          full_video_path: string
          id: string
          is_deleted: boolean
          is_false_positive: boolean
          is_unidentified: boolean
          last_synced_at: string | null
          member_id: number
          notification_sent_at: string | null
          processing_notes: string | null
          processing_segment_id: string | null
          session_date: string | null
          session_type: string | null
          session_uid: string | null
          start_timestamp: string
          status: Database["public"]["Enums"]["parliament_clip_status"] | null
          thumbnail_url: string | null
          transcript: string
          transcript_embedding: string | null
          transcript_manually_edited: boolean
          updated_at: string | null
          vertical_clip_url: string | null
          vertical_thumbnail_url: string | null
        }
        Insert: {
          clip_url?: string | null
          created_at?: string | null
          deleted_at?: string | null
          description?: string | null
          description_embedding?: string | null
          duration_seconds?: number | null
          end_timestamp: string
          full_video_path: string
          id?: string
          is_deleted?: boolean
          is_false_positive?: boolean
          is_unidentified?: boolean
          last_synced_at?: string | null
          member_id: number
          notification_sent_at?: string | null
          processing_notes?: string | null
          processing_segment_id?: string | null
          session_date?: string | null
          session_type?: string | null
          session_uid?: string | null
          start_timestamp: string
          status?: Database["public"]["Enums"]["parliament_clip_status"] | null
          thumbnail_url?: string | null
          transcript: string
          transcript_embedding?: string | null
          transcript_manually_edited?: boolean
          updated_at?: string | null
          vertical_clip_url?: string | null
          vertical_thumbnail_url?: string | null
        }
        Update: {
          clip_url?: string | null
          created_at?: string | null
          deleted_at?: string | null
          description?: string | null
          description_embedding?: string | null
          duration_seconds?: number | null
          end_timestamp?: string
          full_video_path?: string
          id?: string
          is_deleted?: boolean
          is_false_positive?: boolean
          is_unidentified?: boolean
          last_synced_at?: string | null
          member_id?: number
          notification_sent_at?: string | null
          processing_notes?: string | null
          processing_segment_id?: string | null
          session_date?: string | null
          session_type?: string | null
          session_uid?: string | null
          start_timestamp?: string
          status?: Database["public"]["Enums"]["parliament_clip_status"] | null
          thumbnail_url?: string | null
          transcript?: string
          transcript_embedding?: string | null
          transcript_manually_edited?: boolean
          updated_at?: string | null
          vertical_clip_url?: string | null
          vertical_thumbnail_url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "fk_parliament_member_clips_processing_segment_id"
            columns: ["processing_segment_id"]
            isOneToOne: false
            referencedRelation: "event_processing_segments"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fk_parliament_member_clips_session_uid"
            columns: ["session_uid"]
            isOneToOne: false
            referencedRelation: "parliament_events"
            referencedColumns: ["event_id"]
          },
          {
            foreignKeyName: "parliament_member_clips_member_id_fkey"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
        ]
      }
      parliament_member_contacts: {
        Row: {
          address_line_1: string | null
          address_line_2: string | null
          address_line_3: string | null
          address_line_4: string | null
          address_line_5: string | null
          contact_type:
            | Database["public"]["Enums"]["parliament_contact_type"]
            | null
          contact_type_id: number | null
          created_at: string | null
          deleted_at: string | null
          email: string | null
          facebook_url: string | null
          fax: string | null
          id: string
          instagram_url: string | null
          is_deleted: boolean
          is_physical: boolean | null
          is_primary: boolean | null
          last_synced_at: string | null
          linkedin_url: string | null
          member_id: number
          note: string | null
          phone: string | null
          postcode: string | null
          twitter_url: string | null
          updated_at: string | null
          website_display_as: string | null
          website_url: string | null
          youtube_url: string | null
        }
        Insert: {
          address_line_1?: string | null
          address_line_2?: string | null
          address_line_3?: string | null
          address_line_4?: string | null
          address_line_5?: string | null
          contact_type?:
            | Database["public"]["Enums"]["parliament_contact_type"]
            | null
          contact_type_id?: number | null
          created_at?: string | null
          deleted_at?: string | null
          email?: string | null
          facebook_url?: string | null
          fax?: string | null
          id?: string
          instagram_url?: string | null
          is_deleted?: boolean
          is_physical?: boolean | null
          is_primary?: boolean | null
          last_synced_at?: string | null
          linkedin_url?: string | null
          member_id: number
          note?: string | null
          phone?: string | null
          postcode?: string | null
          twitter_url?: string | null
          updated_at?: string | null
          website_display_as?: string | null
          website_url?: string | null
          youtube_url?: string | null
        }
        Update: {
          address_line_1?: string | null
          address_line_2?: string | null
          address_line_3?: string | null
          address_line_4?: string | null
          address_line_5?: string | null
          contact_type?:
            | Database["public"]["Enums"]["parliament_contact_type"]
            | null
          contact_type_id?: number | null
          created_at?: string | null
          deleted_at?: string | null
          email?: string | null
          facebook_url?: string | null
          fax?: string | null
          id?: string
          instagram_url?: string | null
          is_deleted?: boolean
          is_physical?: boolean | null
          is_primary?: boolean | null
          last_synced_at?: string | null
          linkedin_url?: string | null
          member_id?: number
          note?: string | null
          phone?: string | null
          postcode?: string | null
          twitter_url?: string | null
          updated_at?: string | null
          website_display_as?: string | null
          website_url?: string | null
          youtube_url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "parliament_member_contacts_member_id_fkey"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
        ]
      }
      parliament_member_face_encodings: {
        Row: {
          created_at: string | null
          deleted_at: string | null
          detection_confidence: number | null
          encoding_quality: number | null
          error_message: string | null
          face_bbox_bottom: number | null
          face_bbox_left: number | null
          face_bbox_right: number | null
          face_bbox_top: number | null
          face_encoding: string
          face_encoding_json: Json | null
          id: string
          image_height: number | null
          image_width: number | null
          is_active: boolean | null
          is_deleted: boolean
          is_primary_encoding: boolean | null
          is_validated: boolean | null
          last_synced_at: string | null
          member_id: number
          portrait_id: string
          processing_date: string | null
          processing_model: string | null
          processing_notes: string | null
          processing_version: string | null
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          deleted_at?: string | null
          detection_confidence?: number | null
          encoding_quality?: number | null
          error_message?: string | null
          face_bbox_bottom?: number | null
          face_bbox_left?: number | null
          face_bbox_right?: number | null
          face_bbox_top?: number | null
          face_encoding: string
          face_encoding_json?: Json | null
          id?: string
          image_height?: number | null
          image_width?: number | null
          is_active?: boolean | null
          is_deleted?: boolean
          is_primary_encoding?: boolean | null
          is_validated?: boolean | null
          last_synced_at?: string | null
          member_id: number
          portrait_id: string
          processing_date?: string | null
          processing_model?: string | null
          processing_notes?: string | null
          processing_version?: string | null
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          deleted_at?: string | null
          detection_confidence?: number | null
          encoding_quality?: number | null
          error_message?: string | null
          face_bbox_bottom?: number | null
          face_bbox_left?: number | null
          face_bbox_right?: number | null
          face_bbox_top?: number | null
          face_encoding?: string
          face_encoding_json?: Json | null
          id?: string
          image_height?: number | null
          image_width?: number | null
          is_active?: boolean | null
          is_deleted?: boolean
          is_primary_encoding?: boolean | null
          is_validated?: boolean | null
          last_synced_at?: string | null
          member_id?: number
          portrait_id?: string
          processing_date?: string | null
          processing_model?: string | null
          processing_notes?: string | null
          processing_version?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "parliament_member_face_encodings_member_id_fkey"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
          {
            foreignKeyName: "parliament_member_face_encodings_portrait_id_fkey"
            columns: ["portrait_id"]
            isOneToOne: false
            referencedRelation: "parliament_member_portraits"
            referencedColumns: ["id"]
          },
        ]
      }
      parliament_member_portraits: {
        Row: {
          created_at: string | null
          crop_type: number
          deleted_at: string | null
          id: string
          image_url: string
          is_deleted: boolean
          is_primary: boolean | null
          is_valid_mp_image: boolean
          last_synced_at: string | null
          member_id: number
          source: string
          updated_at: string | null
          web_version: boolean | null
        }
        Insert: {
          created_at?: string | null
          crop_type: number
          deleted_at?: string | null
          id?: string
          image_url: string
          is_deleted?: boolean
          is_primary?: boolean | null
          is_valid_mp_image?: boolean
          last_synced_at?: string | null
          member_id: number
          source?: string
          updated_at?: string | null
          web_version?: boolean | null
        }
        Update: {
          created_at?: string | null
          crop_type?: number
          deleted_at?: string | null
          id?: string
          image_url?: string
          is_deleted?: boolean
          is_primary?: boolean | null
          is_valid_mp_image?: boolean
          last_synced_at?: string | null
          member_id?: number
          source?: string
          updated_at?: string | null
          web_version?: boolean | null
        }
        Relationships: [
          {
            foreignKeyName: "parliament_member_portraits_member_id_fkey"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
        ]
      }
      parliament_member_voting_history: {
        Row: {
          acted_as_teller: boolean | null
          created_at: string | null
          deleted_at: string | null
          division_date: string | null
          division_id: number | null
          division_number: number | null
          division_result:
            | Database["public"]["Enums"]["parliament_division_result"]
            | null
          division_title: string | null
          house_id: number | null
          house_name: Database["public"]["Enums"]["parliament_house"] | null
          id: string
          in_affirmative_lobby: boolean | null
          is_deleted: boolean
          last_synced_at: string | null
          member_id: number
          number_against: number | null
          number_in_favour: number | null
          updated_at: string | null
        }
        Insert: {
          acted_as_teller?: boolean | null
          created_at?: string | null
          deleted_at?: string | null
          division_date?: string | null
          division_id?: number | null
          division_number?: number | null
          division_result?:
            | Database["public"]["Enums"]["parliament_division_result"]
            | null
          division_title?: string | null
          house_id?: number | null
          house_name?: Database["public"]["Enums"]["parliament_house"] | null
          id?: string
          in_affirmative_lobby?: boolean | null
          is_deleted?: boolean
          last_synced_at?: string | null
          member_id: number
          number_against?: number | null
          number_in_favour?: number | null
          updated_at?: string | null
        }
        Update: {
          acted_as_teller?: boolean | null
          created_at?: string | null
          deleted_at?: string | null
          division_date?: string | null
          division_id?: number | null
          division_number?: number | null
          division_result?:
            | Database["public"]["Enums"]["parliament_division_result"]
            | null
          division_title?: string | null
          house_id?: number | null
          house_name?: Database["public"]["Enums"]["parliament_house"] | null
          id?: string
          in_affirmative_lobby?: boolean | null
          is_deleted?: boolean
          last_synced_at?: string | null
          member_id?: number
          number_against?: number | null
          number_in_favour?: number | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "parliament_member_voting_history_member_id_fkey"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
        ]
      }
      parliament_members: {
        Row: {
          constituency_end_date: string | null
          constituency_id: number | null
          constituency_name: string | null
          constituency_start_date: string | null
          created_at: string | null
          date_of_birth: string | null
          date_of_death: string | null
          deleted_at: string | null
          display_name: string | null
          family_name: string | null
          full_title: string | null
          gender: Database["public"]["Enums"]["parliament_gender"] | null
          given_name: string | null
          house_id: number | null
          house_name: Database["public"]["Enums"]["parliament_house"] | null
          id: string
          is_current_member: boolean | null
          is_deleted: boolean
          is_eligible: boolean | null
          last_synced_at: string | null
          list_as: string | null
          lords_membership_type: string | null
          lords_membership_type_id: number | null
          member_id: number
          membership_end_date: string | null
          membership_end_reason: string | null
          membership_start_date: string | null
          membership_start_reason: string | null
          party_abbreviation: string | null
          party_background_colour: string | null
          party_foreground_colour: string | null
          party_id: number | null
          party_is_independent: boolean | null
          party_is_lord_spiritual: boolean | null
          party_name: string | null
          updated_at: string | null
        }
        Insert: {
          constituency_end_date?: string | null
          constituency_id?: number | null
          constituency_name?: string | null
          constituency_start_date?: string | null
          created_at?: string | null
          date_of_birth?: string | null
          date_of_death?: string | null
          deleted_at?: string | null
          display_name?: string | null
          family_name?: string | null
          full_title?: string | null
          gender?: Database["public"]["Enums"]["parliament_gender"] | null
          given_name?: string | null
          house_id?: number | null
          house_name?: Database["public"]["Enums"]["parliament_house"] | null
          id?: string
          is_current_member?: boolean | null
          is_deleted?: boolean
          is_eligible?: boolean | null
          last_synced_at?: string | null
          list_as?: string | null
          lords_membership_type?: string | null
          lords_membership_type_id?: number | null
          member_id: number
          membership_end_date?: string | null
          membership_end_reason?: string | null
          membership_start_date?: string | null
          membership_start_reason?: string | null
          party_abbreviation?: string | null
          party_background_colour?: string | null
          party_foreground_colour?: string | null
          party_id?: number | null
          party_is_independent?: boolean | null
          party_is_lord_spiritual?: boolean | null
          party_name?: string | null
          updated_at?: string | null
        }
        Update: {
          constituency_end_date?: string | null
          constituency_id?: number | null
          constituency_name?: string | null
          constituency_start_date?: string | null
          created_at?: string | null
          date_of_birth?: string | null
          date_of_death?: string | null
          deleted_at?: string | null
          display_name?: string | null
          family_name?: string | null
          full_title?: string | null
          gender?: Database["public"]["Enums"]["parliament_gender"] | null
          given_name?: string | null
          house_id?: number | null
          house_name?: Database["public"]["Enums"]["parliament_house"] | null
          id?: string
          is_current_member?: boolean | null
          is_deleted?: boolean
          is_eligible?: boolean | null
          last_synced_at?: string | null
          list_as?: string | null
          lords_membership_type?: string | null
          lords_membership_type_id?: number | null
          member_id?: number
          membership_end_date?: string | null
          membership_end_reason?: string | null
          membership_start_date?: string | null
          membership_start_reason?: string | null
          party_abbreviation?: string | null
          party_background_colour?: string | null
          party_foreground_colour?: string | null
          party_id?: number | null
          party_is_independent?: boolean | null
          party_is_lord_spiritual?: boolean | null
          party_name?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      parliament_sync_logs: {
        Row: {
          error_message: string | null
          executed_at: string | null
          id: string
          notes: string | null
          response_status: number | null
          status: Database["public"]["Enums"]["parliament_sync_status_enum"]
          sync_type: Database["public"]["Enums"]["parliament_sync_type"]
        }
        Insert: {
          error_message?: string | null
          executed_at?: string | null
          id?: string
          notes?: string | null
          response_status?: number | null
          status: Database["public"]["Enums"]["parliament_sync_status_enum"]
          sync_type: Database["public"]["Enums"]["parliament_sync_type"]
        }
        Update: {
          error_message?: string | null
          executed_at?: string | null
          id?: string
          notes?: string | null
          response_status?: number | null
          status?: Database["public"]["Enums"]["parliament_sync_status_enum"]
          sync_type?: Database["public"]["Enums"]["parliament_sync_type"]
        }
        Relationships: []
      }
      parliament_sync_status: {
        Row: {
          created_at: string | null
          duration_seconds: number | null
          error_message: string | null
          id: string
          last_sync_at: string | null
          next_sync_at: string | null
          records_failed: number | null
          records_processed: number | null
          status:
            | Database["public"]["Enums"]["parliament_sync_status_enum"]
            | null
          sync_type: Database["public"]["Enums"]["parliament_sync_type"]
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          id?: string
          last_sync_at?: string | null
          next_sync_at?: string | null
          records_failed?: number | null
          records_processed?: number | null
          status?:
            | Database["public"]["Enums"]["parliament_sync_status_enum"]
            | null
          sync_type: Database["public"]["Enums"]["parliament_sync_type"]
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          id?: string
          last_sync_at?: string | null
          next_sync_at?: string | null
          records_failed?: number | null
          records_processed?: number | null
          status?:
            | Database["public"]["Enums"]["parliament_sync_status_enum"]
            | null
          sync_type?: Database["public"]["Enums"]["parliament_sync_type"]
          updated_at?: string | null
        }
        Relationships: []
      }
      portrait_collection_evaluations: {
        Row: {
          created_at: string | null
          evaluated_by: string
          id: string
          locked_at: string | null
          locked_by: string | null
          member_id_selected: number | null
          portraits_added: string[]
          processing_run_id: string
          rejected_face_indices: number[]
          segment_id: string
          selected_face_indices: number[]
          skip_reason: Database["public"]["Enums"]["skip_reason_type"] | null
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          evaluated_by: string
          id?: string
          locked_at?: string | null
          locked_by?: string | null
          member_id_selected?: number | null
          portraits_added?: string[]
          processing_run_id: string
          rejected_face_indices?: number[]
          segment_id: string
          selected_face_indices?: number[]
          skip_reason?: Database["public"]["Enums"]["skip_reason_type"] | null
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          evaluated_by?: string
          id?: string
          locked_at?: string | null
          locked_by?: string | null
          member_id_selected?: number | null
          portraits_added?: string[]
          processing_run_id?: string
          rejected_face_indices?: number[]
          segment_id?: string
          selected_face_indices?: number[]
          skip_reason?: Database["public"]["Enums"]["skip_reason_type"] | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "portrait_collection_evaluations_member_id_selected_fkey"
            columns: ["member_id_selected"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
          {
            foreignKeyName: "portrait_collection_evaluations_processing_run_id_fkey"
            columns: ["processing_run_id"]
            isOneToOne: false
            referencedRelation: "event_processing_runs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "portrait_collection_evaluations_segment_id_fkey"
            columns: ["segment_id"]
            isOneToOne: true
            referencedRelation: "event_processing_segments"
            referencedColumns: ["id"]
          },
        ]
      }
      runpod_processing_logs: {
        Row: {
          created_at: string | null
          endpoint: string
          error_message: string | null
          id: string
          notes: string | null
          record_id: string
          response_status: number | null
          status: string
          table_name: string
        }
        Insert: {
          created_at?: string | null
          endpoint: string
          error_message?: string | null
          id?: string
          notes?: string | null
          record_id: string
          response_status?: number | null
          status: string
          table_name: string
        }
        Update: {
          created_at?: string | null
          endpoint?: string
          error_message?: string | null
          id?: string
          notes?: string | null
          record_id?: string
          response_status?: number | null
          status?: string
          table_name?: string
        }
        Relationships: []
      }
      segment_evaluations: {
        Row: {
          created_at: string | null
          error_reason:
            | Database["public"]["Enums"]["segment_evaluation_error_reason"]
            | null
          evaluated_by: string
          id: string
          is_correct: boolean | null
          locked_at: string | null
          locked_by: string | null
          processing_run_id: string
          segment_id: string
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          error_reason?:
            | Database["public"]["Enums"]["segment_evaluation_error_reason"]
            | null
          evaluated_by: string
          id?: string
          is_correct?: boolean | null
          locked_at?: string | null
          locked_by?: string | null
          processing_run_id: string
          segment_id: string
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          error_reason?:
            | Database["public"]["Enums"]["segment_evaluation_error_reason"]
            | null
          evaluated_by?: string
          id?: string
          is_correct?: boolean | null
          locked_at?: string | null
          locked_by?: string | null
          processing_run_id?: string
          segment_id?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "segment_evaluations_processing_run_id_fkey"
            columns: ["processing_run_id"]
            isOneToOne: false
            referencedRelation: "event_processing_runs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "segment_evaluations_segment_id_fkey"
            columns: ["segment_id"]
            isOneToOne: true
            referencedRelation: "event_processing_segments"
            referencedColumns: ["id"]
          },
        ]
      }
      segment_portrait_matches: {
        Row: {
          created_at: string | null
          face_encoding_id: string
          face_index: number | null
          id: string
          is_top_candidate: boolean | null
          member_id: number
          segment_id: string
          similarity: number | null
          was_selected: boolean | null
        }
        Insert: {
          created_at?: string | null
          face_encoding_id: string
          face_index?: number | null
          id?: string
          is_top_candidate?: boolean | null
          member_id: number
          segment_id: string
          similarity?: number | null
          was_selected?: boolean | null
        }
        Update: {
          created_at?: string | null
          face_encoding_id?: string
          face_index?: number | null
          id?: string
          is_top_candidate?: boolean | null
          member_id?: number
          segment_id?: string
          similarity?: number | null
          was_selected?: boolean | null
        }
        Relationships: [
          {
            foreignKeyName: "fk_portrait_matches_face_encoding_id"
            columns: ["face_encoding_id"]
            isOneToOne: false
            referencedRelation: "parliament_member_face_encodings"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fk_portrait_matches_member_id"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
          {
            foreignKeyName: "fk_portrait_matches_segment_id"
            columns: ["segment_id"]
            isOneToOne: false
            referencedRelation: "event_processing_segments"
            referencedColumns: ["id"]
          },
        ]
      }
      segment_speaker_faces: {
        Row: {
          confidence: number | null
          created_at: string | null
          face_index: number
          face_size: number | null
          frontal_score: number | null
          id: string
          is_frontal: boolean | null
          occlusion_score: number | null
          quality_score: number | null
          s3_url: string | null
          segment_id: string
          size_score: number | null
        }
        Insert: {
          confidence?: number | null
          created_at?: string | null
          face_index: number
          face_size?: number | null
          frontal_score?: number | null
          id?: string
          is_frontal?: boolean | null
          occlusion_score?: number | null
          quality_score?: number | null
          s3_url?: string | null
          segment_id: string
          size_score?: number | null
        }
        Update: {
          confidence?: number | null
          created_at?: string | null
          face_index?: number
          face_size?: number | null
          frontal_score?: number | null
          id?: string
          is_frontal?: boolean | null
          occlusion_score?: number | null
          quality_score?: number | null
          s3_url?: string | null
          segment_id?: string
          size_score?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "fk_speaker_faces_segment_id"
            columns: ["segment_id"]
            isOneToOne: false
            referencedRelation: "event_processing_segments"
            referencedColumns: ["id"]
          },
        ]
      }
      terms_acceptances: {
        Row: {
          accepted_at: string
          accepted_via: string
          user_id: string
        }
        Insert: {
          accepted_at?: string
          accepted_via: string
          user_id: string
        }
        Update: {
          accepted_at?: string
          accepted_via?: string
          user_id?: string
        }
        Relationships: []
      }
      team_invitations: {
        Row: {
          accepted_at: string | null
          accepted_by: string | null
          created_at: string | null
          email: string
          expires_at: string
          id: string
          invited_by: string
          last_resent_at: string | null
          role: Database["public"]["Enums"]["team_role"]
          team_id: string
          token: string
        }
        Insert: {
          accepted_at?: string | null
          accepted_by?: string | null
          created_at?: string | null
          email: string
          expires_at?: string
          id?: string
          invited_by: string
          last_resent_at?: string | null
          role?: Database["public"]["Enums"]["team_role"]
          team_id: string
          token: string
        }
        Update: {
          accepted_at?: string | null
          accepted_by?: string | null
          created_at?: string | null
          email?: string
          expires_at?: string
          id?: string
          invited_by?: string
          last_resent_at?: string | null
          role?: Database["public"]["Enums"]["team_role"]
          team_id?: string
          token?: string
        }
        Relationships: [
          {
            foreignKeyName: "team_invitations_team_id_fkey"
            columns: ["team_id"]
            isOneToOne: false
            referencedRelation: "teams"
            referencedColumns: ["id"]
          },
        ]
      }
      team_members: {
        Row: {
          id: string
          invited_by: string | null
          joined_at: string | null
          role: Database["public"]["Enums"]["team_role"]
          team_id: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          id?: string
          invited_by?: string | null
          joined_at?: string | null
          role?: Database["public"]["Enums"]["team_role"]
          team_id: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          id?: string
          invited_by?: string | null
          joined_at?: string | null
          role?: Database["public"]["Enums"]["team_role"]
          team_id?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "team_members_team_id_fkey"
            columns: ["team_id"]
            isOneToOne: false
            referencedRelation: "teams"
            referencedColumns: ["id"]
          },
        ]
      }
      team_mp_follows: {
        Row: {
          followed_at: string | null
          followed_by: string
          id: string
          member_id: number
          team_id: string
        }
        Insert: {
          followed_at?: string | null
          followed_by: string
          id?: string
          member_id: number
          team_id: string
        }
        Update: {
          followed_at?: string | null
          followed_by?: string
          id?: string
          member_id?: number
          team_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "team_mp_follows_member_id_fkey"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
          {
            foreignKeyName: "team_mp_follows_team_id_fkey"
            columns: ["team_id"]
            isOneToOne: false
            referencedRelation: "teams"
            referencedColumns: ["id"]
          },
        ]
      }
      team_notification_preferences: {
        Row: {
          clip_processing_notifications: boolean | null
          created_at: string | null
          email_notifications: boolean | null
          id: string
          in_app_notifications: boolean | null
          mp_activity_notifications: boolean | null
          team_activity_notifications: boolean | null
          team_id: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          clip_processing_notifications?: boolean | null
          created_at?: string | null
          email_notifications?: boolean | null
          id?: string
          in_app_notifications?: boolean | null
          mp_activity_notifications?: boolean | null
          team_activity_notifications?: boolean | null
          team_id: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          clip_processing_notifications?: boolean | null
          created_at?: string | null
          email_notifications?: boolean | null
          id?: string
          in_app_notifications?: boolean | null
          mp_activity_notifications?: boolean | null
          team_activity_notifications?: boolean | null
          team_id?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "team_notification_preferences_team_id_fkey"
            columns: ["team_id"]
            isOneToOne: false
            referencedRelation: "teams"
            referencedColumns: ["id"]
          },
        ]
      }
      teams: {
        Row: {
          created_at: string | null
          deleted_at: string | null
          description: string | null
          id: string
          is_deleted: boolean
          name: string
          owner_id: string
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          deleted_at?: string | null
          description?: string | null
          id?: string
          is_deleted?: boolean
          name: string
          owner_id: string
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          deleted_at?: string | null
          description?: string | null
          id?: string
          is_deleted?: boolean
          name?: string
          owner_id?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      transcript_embedding_logs: {
        Row: {
          clip_id: string
          created_at: string | null
          error_message: string | null
          id: string
          notes: string | null
          response_status: number | null
          status: string
          table_name: string
          transcript_length: number | null
        }
        Insert: {
          clip_id: string
          created_at?: string | null
          error_message?: string | null
          id?: string
          notes?: string | null
          response_status?: number | null
          status: string
          table_name: string
          transcript_length?: number | null
        }
        Update: {
          clip_id?: string
          created_at?: string | null
          error_message?: string | null
          id?: string
          notes?: string | null
          response_status?: number | null
          status?: string
          table_name?: string
          transcript_length?: number | null
        }
        Relationships: []
      }
      user_clips: {
        Row: {
          audio_sample_rate: number | null
          bluesky_post_ids: string[] | null
          clip_duration_seconds: number | null
          clip_id: string
          clip_url: string | null
          composition_json: Json | null
          cost_estimate_usd: number | null
          created_at: string | null
          deleted_at: string | null
          description: string | null
          description_embedding: string | null
          duration: string | null
          editor_version: number
          error_message: string | null
          facebook_post_ids: string[] | null
          failed_steps: string[] | null
          full_video_path: string | null
          gpu_memory_used_gb: number | null
          gpu_model: string | null
          id: string
          input_video_size_mb: number | null
          instagram_post_ids: string[] | null
          instagram_standalone_post_ids: string[] | null
          is_deleted: boolean
          linkedin_page_post_ids: string[] | null
          linkedin_post_ids: string[] | null
          mastodon_post_ids: string[] | null
          num_segments_processed: number | null
          output_clip_size_mb: number | null
          output_vertical_clip_size_mb: number | null
          peak_memory_usage_gb: number | null
          processing_completed_at: string | null
          processing_node: string | null
          processing_started_at: string | null
          processing_time_clip_creation: number | null
          processing_time_download: number | null
          processing_time_total: number | null
          processing_time_transcript: number | null
          processing_time_upload: number | null
          queue_wait_time_seconds: number | null
          retry_count: number | null
          segments: Json | null
          session_uid: string | null
          status: Database["public"]["Enums"]["parliament_clip_status"] | null
          team_id: string | null
          threads_post_ids: string[] | null
          thumbnail_url: string | null
          tiktok_post_ids: string[] | null
          title: string | null
          title_embedding: string | null
          transcript: string | null
          transcript_confidence_score: number | null
          transcript_embedding: string | null
          transcript_manually_edited: boolean
          transcript_word_count: number | null
          twitter_post_ids: string[] | null
          updated_at: string | null
          user_id: string | null
          vertical_clip_url: string | null
          vertical_thumbnail_url: string | null
          video_bitrate_kbps: number | null
          video_resolution: string | null
          view_count: number
          warnings: string[] | null
          watermark_position:
            | Database["public"]["Enums"]["watermark_position"]
            | null
          watermark_url: string | null
          worker_id: string | null
          youtube_post_ids: string[] | null
        }
        Insert: {
          audio_sample_rate?: number | null
          bluesky_post_ids?: string[] | null
          clip_duration_seconds?: number | null
          clip_id: string
          clip_url?: string | null
          composition_json?: Json | null
          cost_estimate_usd?: number | null
          created_at?: string | null
          deleted_at?: string | null
          description?: string | null
          description_embedding?: string | null
          duration?: string | null
          editor_version?: number
          error_message?: string | null
          facebook_post_ids?: string[] | null
          failed_steps?: string[] | null
          full_video_path?: string | null
          gpu_memory_used_gb?: number | null
          gpu_model?: string | null
          id?: string
          input_video_size_mb?: number | null
          instagram_post_ids?: string[] | null
          instagram_standalone_post_ids?: string[] | null
          is_deleted?: boolean
          linkedin_page_post_ids?: string[] | null
          linkedin_post_ids?: string[] | null
          mastodon_post_ids?: string[] | null
          num_segments_processed?: number | null
          output_clip_size_mb?: number | null
          output_vertical_clip_size_mb?: number | null
          peak_memory_usage_gb?: number | null
          processing_completed_at?: string | null
          processing_node?: string | null
          processing_started_at?: string | null
          processing_time_clip_creation?: number | null
          processing_time_download?: number | null
          processing_time_total?: number | null
          processing_time_transcript?: number | null
          processing_time_upload?: number | null
          queue_wait_time_seconds?: number | null
          retry_count?: number | null
          segments?: Json | null
          session_uid?: string | null
          status?: Database["public"]["Enums"]["parliament_clip_status"] | null
          team_id?: string | null
          threads_post_ids?: string[] | null
          thumbnail_url?: string | null
          tiktok_post_ids?: string[] | null
          title?: string | null
          title_embedding?: string | null
          transcript?: string | null
          transcript_confidence_score?: number | null
          transcript_embedding?: string | null
          transcript_manually_edited?: boolean
          transcript_word_count?: number | null
          twitter_post_ids?: string[] | null
          updated_at?: string | null
          user_id?: string | null
          vertical_clip_url?: string | null
          vertical_thumbnail_url?: string | null
          video_bitrate_kbps?: number | null
          video_resolution?: string | null
          view_count?: number
          warnings?: string[] | null
          watermark_position?:
            | Database["public"]["Enums"]["watermark_position"]
            | null
          watermark_url?: string | null
          worker_id?: string | null
          youtube_post_ids?: string[] | null
        }
        Update: {
          audio_sample_rate?: number | null
          bluesky_post_ids?: string[] | null
          clip_duration_seconds?: number | null
          clip_id?: string
          clip_url?: string | null
          composition_json?: Json | null
          cost_estimate_usd?: number | null
          created_at?: string | null
          deleted_at?: string | null
          description?: string | null
          description_embedding?: string | null
          duration?: string | null
          editor_version?: number
          error_message?: string | null
          facebook_post_ids?: string[] | null
          failed_steps?: string[] | null
          full_video_path?: string | null
          gpu_memory_used_gb?: number | null
          gpu_model?: string | null
          id?: string
          input_video_size_mb?: number | null
          instagram_post_ids?: string[] | null
          instagram_standalone_post_ids?: string[] | null
          is_deleted?: boolean
          linkedin_page_post_ids?: string[] | null
          linkedin_post_ids?: string[] | null
          mastodon_post_ids?: string[] | null
          num_segments_processed?: number | null
          output_clip_size_mb?: number | null
          output_vertical_clip_size_mb?: number | null
          peak_memory_usage_gb?: number | null
          processing_completed_at?: string | null
          processing_node?: string | null
          processing_started_at?: string | null
          processing_time_clip_creation?: number | null
          processing_time_download?: number | null
          processing_time_total?: number | null
          processing_time_transcript?: number | null
          processing_time_upload?: number | null
          queue_wait_time_seconds?: number | null
          retry_count?: number | null
          segments?: Json | null
          session_uid?: string | null
          status?: Database["public"]["Enums"]["parliament_clip_status"] | null
          team_id?: string | null
          threads_post_ids?: string[] | null
          thumbnail_url?: string | null
          tiktok_post_ids?: string[] | null
          title?: string | null
          title_embedding?: string | null
          transcript?: string | null
          transcript_confidence_score?: number | null
          transcript_embedding?: string | null
          transcript_manually_edited?: boolean
          transcript_word_count?: number | null
          twitter_post_ids?: string[] | null
          updated_at?: string | null
          user_id?: string | null
          vertical_clip_url?: string | null
          vertical_thumbnail_url?: string | null
          video_bitrate_kbps?: number | null
          video_resolution?: string | null
          view_count?: number
          warnings?: string[] | null
          watermark_position?:
            | Database["public"]["Enums"]["watermark_position"]
            | null
          watermark_url?: string | null
          worker_id?: string | null
          youtube_post_ids?: string[] | null
        }
        Relationships: [
          {
            foreignKeyName: "user_clips_clip_id_fkey"
            columns: ["clip_id"]
            isOneToOne: false
            referencedRelation: "parliament_member_clips"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_clips_team_id_fkey"
            columns: ["team_id"]
            isOneToOne: false
            referencedRelation: "teams"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          bluesky_avatar: string | null
          bluesky_display_name: string | null
          bluesky_identifier: string | null
          bluesky_password: string | null
          bluesky_service: string | null
          clip_processing_complete: boolean
          created_at: string
          email: string
          id: number
          is_first_login: boolean
          is_online: boolean
          is_stripe_account_active: boolean
          member_id: number | null
          new_clips_available: boolean
          postiz_api_key: string | null
          postiz_email: string | null
          postiz_password: string | null
          role: Database["public"]["Enums"]["app_role"]
          social_media_shares: boolean
          stripe_account_id: string | null
          stripe_customer_id: string | null
          system_updates: boolean
          updated_at: string
          user_id: string
          username: string | null
          weekly_performance_report: boolean
        }
        Insert: {
          bluesky_avatar?: string | null
          bluesky_display_name?: string | null
          bluesky_identifier?: string | null
          bluesky_password?: string | null
          bluesky_service?: string | null
          clip_processing_complete?: boolean
          created_at?: string
          email: string
          id?: number
          is_first_login?: boolean
          is_online?: boolean
          is_stripe_account_active?: boolean
          member_id?: number | null
          new_clips_available?: boolean
          postiz_api_key?: string | null
          postiz_email?: string | null
          postiz_password?: string | null
          role?: Database["public"]["Enums"]["app_role"]
          social_media_shares?: boolean
          stripe_account_id?: string | null
          stripe_customer_id?: string | null
          system_updates?: boolean
          updated_at?: string
          user_id: string
          username?: string | null
          weekly_performance_report?: boolean
        }
        Update: {
          bluesky_avatar?: string | null
          bluesky_display_name?: string | null
          bluesky_identifier?: string | null
          bluesky_password?: string | null
          bluesky_service?: string | null
          clip_processing_complete?: boolean
          created_at?: string
          email?: string
          id?: number
          is_first_login?: boolean
          is_online?: boolean
          is_stripe_account_active?: boolean
          member_id?: number | null
          new_clips_available?: boolean
          postiz_api_key?: string | null
          postiz_email?: string | null
          postiz_password?: string | null
          role?: Database["public"]["Enums"]["app_role"]
          social_media_shares?: boolean
          stripe_account_id?: string | null
          stripe_customer_id?: string | null
          system_updates?: boolean
          updated_at?: string
          user_id?: string
          username?: string | null
          weekly_performance_report?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "user_roles_member_id_fkey"
            columns: ["member_id"]
            isOneToOne: false
            referencedRelation: "parliament_members"
            referencedColumns: ["member_id"]
          },
        ]
      }
      video_jobs: {
        Row: {
          created_at: string | null
          error_message: string | null
          horizontal_video_url: string | null
          id: string
          job_id: string
          message: string
          progress: number
          stage: string
          updated_at: string | null
          user_clip_id: string | null
          user_id: string
          vertical_video_url: string | null
        }
        Insert: {
          created_at?: string | null
          error_message?: string | null
          horizontal_video_url?: string | null
          id?: string
          job_id: string
          message?: string
          progress?: number
          stage: string
          updated_at?: string | null
          user_clip_id?: string | null
          user_id: string
          vertical_video_url?: string | null
        }
        Update: {
          created_at?: string | null
          error_message?: string | null
          horizontal_video_url?: string | null
          id?: string
          job_id?: string
          message?: string
          progress?: number
          stage?: string
          updated_at?: string | null
          user_clip_id?: string | null
          user_id?: string
          vertical_video_url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "video_jobs_user_clip_id_fkey"
            columns: ["user_clip_id"]
            isOneToOne: false
            referencedRelation: "user_clips"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      queue_info: {
        Row: {
          created_at: string | null
          is_partitioned: boolean | null
          is_unlogged: boolean | null
          queue_name: string | null
        }
        Relationships: []
      }
      video_storage_activity: {
        Row: {
          action_type: string | null
          bucket_id: string | null
          created_at: string | null
          metadata: Json | null
          name: string | null
          updated_at: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      accept_team_invitation: {
        Args: { p_token: string; p_user_id: string }
        Returns: {
          message: string
          success: boolean
          team_id: string
          team_name: string
        }[]
      }
      add_clip_segment: {
        Args: {
          clip_id: string
          p_end_timestamp: string
          p_start_timestamp: string
        }
        Returns: boolean
      }
      bytea_to_text: { Args: { data: string }; Returns: string }
      call_parliament_event_sync_endpoint: { Args: never; Returns: Json }
      call_parliament_sync_endpoint: { Args: never; Returns: Json }
      call_parliament_sync_endpoint_with_voting: {
        Args: never
        Returns: undefined
      }
      call_video_sync_endpoint: {
        Args: { file_name?: string }
        Returns: undefined
      }
      can_publish_to_social: {
        Args: { p_team_id: string; p_user_id: string }
        Returns: boolean
      }
      cleanup_old_video_jobs: { Args: never; Returns: undefined }
      custom_access_token_hook: { Args: { event: Json }; Returns: Json }
      generate_invitation_token: { Args: never; Returns: string }
      generate_missing_embeddings_batch: {
        Args: { limit_param?: number; table_name_param?: string }
        Returns: {
          clips_found: number
          clips_processed: number
          clips_queued: number
          failed_count: number
          success_count: number
        }[]
      }
      get_clip_segments: {
        Args: { clip_id: string }
        Returns: {
          end_timestamp: string
          start_timestamp: string
        }[]
      }
      get_embedding_generation_status: {
        Args: { clip_id_param: string }
        Returns: {
          clip_id: string
          created_at: string
          error_message: string
          notes: string
          response_status: number
          status: string
          table_name: string
          transcript_length: number
        }[]
      }
      get_embedding_queue_status: {
        Args: never
        Returns: {
          failed_logs_count: number
          newest_msg_age_sec: number
          oldest_msg_age_sec: number
          pending_logs_count: number
          queue_length: number
          success_logs_count: number
          total_messages: number
        }[]
      }
      get_parliament_cron_jobs: {
        Args: never
        Returns: {
          active: boolean
          command: string
          job_id: number
          job_name: string
          schedule: string
        }[]
      }
      get_runpod_processing_status: {
        Args: { record_id_param: string }
        Returns: {
          created_at: string
          endpoint: string
          error_message: string
          notes: string
          record_id: string
          response_status: number
          status: string
          table_name: string
        }[]
      }
      get_team_role: {
        Args: { p_team_id: string; p_user_id: string }
        Returns: Database["public"]["Enums"]["team_role"]
      }
      get_team_stats: {
        Args: { p_team_id: string }
        Returns: {
          followed_mp_count: number
          total_administrators: number
          total_clips: number
          total_members: number
          total_users: number
        }[]
      }
      get_user_email: { Args: { p_user_id: string }; Returns: string }
      get_user_info: {
        Args: { p_user_id: string }
        Returns: {
          email: string
          username: string
        }[]
      }
      get_user_teams: {
        Args: { p_user_id: string }
        Returns: {
          is_owner: boolean
          joined_at: string
          team_description: string
          team_id: string
          team_name: string
          user_role: Database["public"]["Enums"]["team_role"]
        }[]
      }
      http: {
        Args: { request: Database["public"]["CompositeTypes"]["http_request"] }
        Returns: Database["public"]["CompositeTypes"]["http_response"]
        SetofOptions: {
          from: "http_request"
          to: "http_response"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      http_delete:
        | {
            Args: { uri: string }
            Returns: Database["public"]["CompositeTypes"]["http_response"]
            SetofOptions: {
              from: "*"
              to: "http_response"
              isOneToOne: true
              isSetofReturn: false
            }
          }
        | {
            Args: { content: string; content_type: string; uri: string }
            Returns: Database["public"]["CompositeTypes"]["http_response"]
            SetofOptions: {
              from: "*"
              to: "http_response"
              isOneToOne: true
              isSetofReturn: false
            }
          }
      http_get:
        | {
            Args: { uri: string }
            Returns: Database["public"]["CompositeTypes"]["http_response"]
            SetofOptions: {
              from: "*"
              to: "http_response"
              isOneToOne: true
              isSetofReturn: false
            }
          }
        | {
            Args: { data: Json; uri: string }
            Returns: Database["public"]["CompositeTypes"]["http_response"]
            SetofOptions: {
              from: "*"
              to: "http_response"
              isOneToOne: true
              isSetofReturn: false
            }
          }
      http_head: {
        Args: { uri: string }
        Returns: Database["public"]["CompositeTypes"]["http_response"]
        SetofOptions: {
          from: "*"
          to: "http_response"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      http_header: {
        Args: { field: string; value: string }
        Returns: Database["public"]["CompositeTypes"]["http_header"]
        SetofOptions: {
          from: "*"
          to: "http_header"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      http_list_curlopt: {
        Args: never
        Returns: {
          curlopt: string
          value: string
        }[]
      }
      http_patch: {
        Args: { content: string; content_type: string; uri: string }
        Returns: Database["public"]["CompositeTypes"]["http_response"]
        SetofOptions: {
          from: "*"
          to: "http_response"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      http_post:
        | {
            Args: { content: string; content_type: string; uri: string }
            Returns: Database["public"]["CompositeTypes"]["http_response"]
            SetofOptions: {
              from: "*"
              to: "http_response"
              isOneToOne: true
              isSetofReturn: false
            }
          }
        | {
            Args: { data: Json; uri: string }
            Returns: Database["public"]["CompositeTypes"]["http_response"]
            SetofOptions: {
              from: "*"
              to: "http_response"
              isOneToOne: true
              isSetofReturn: false
            }
          }
      http_put: {
        Args: { content: string; content_type: string; uri: string }
        Returns: Database["public"]["CompositeTypes"]["http_response"]
        SetofOptions: {
          from: "*"
          to: "http_response"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      http_reset_curlopt: { Args: never; Returns: boolean }
      http_set_curlopt: {
        Args: { curlopt: string; value: string }
        Returns: boolean
      }
      hybrid_search_parliament_clips: {
        Args: {
          fulltext_query: string
          fulltext_weight?: number
          match_count?: number
          query_embedding_text: string
          rrf_k?: number
          semantic_weight?: number
          target_member_id: number
        }
        Returns: {
          clip_url: string
          created_at: string
          description: string
          duration_seconds: number
          end_timestamp: string
          hybrid_score: number
          id: string
          member_id: number
          session_date: string
          session_type: string
          session_uid: string
          start_timestamp: string
          status: Database["public"]["Enums"]["parliament_clip_status"]
          thumbnail_url: string
          transcript: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
        }[]
      }
      hybrid_search_parliament_clips_all: {
        Args: {
          fulltext_query: string
          fulltext_weight?: number
          match_count?: number
          query_embedding_text: string
          rrf_k?: number
          semantic_weight?: number
          target_member_ids?: number[]
        }
        Returns: {
          clip_url: string
          created_at: string
          description: string
          duration_seconds: number
          end_timestamp: string
          hybrid_score: number
          id: string
          member_id: number
          session_date: string
          session_type: string
          session_uid: string
          start_timestamp: string
          status: Database["public"]["Enums"]["parliament_clip_status"]
          thumbnail_url: string
          transcript: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
        }[]
      }
      is_team_member: {
        Args: { p_team_id: string; p_user_id: string }
        Returns: boolean
      }
      is_valid_timestamp_format: { Args: { ts: string }; Returns: boolean }
      is_veedoo_user: { Args: { p_user_id: string }; Returns: boolean }
      notify_clip_webhook:
        | { Args: never; Returns: undefined }
        | { Args: { clip_id: string }; Returns: undefined }
      prepare_search_terms: { Args: { search_text: string }; Returns: string[] }
      process_embedding_queue: {
        Args: { batch_size?: number; visibility_timeout?: number }
        Returns: {
          failed_count: number
          processed_count: number
          remaining_in_queue: number
          success_count: number
        }[]
      }
      process_queued_embeddings: {
        Args: { batch_size?: number; table_filter?: string }
        Returns: {
          failed_count: number
          processed_count: number
          remaining_queued: number
          success_count: number
        }[]
      }
      process_webhook_queue: {
        Args: { batch_size?: number; visibility_timeout?: number }
        Returns: {
          failed_count: number
          processed_count: number
          remaining_in_queue: number
          success_count: number
        }[]
      }
      queue_missing_embeddings: {
        Args: { limit_param?: number; table_name_param?: string }
        Returns: {
          clips_found: number
          clips_queued: number
        }[]
      }
      search_clips_by_embedding: {
        Args: {
          match_limit?: number
          search_query: string
          similarity_threshold?: number
          target_member_id: number
        }
        Returns: {
          clip_url: string
          created_at: string
          description: string
          duration_seconds: number
          end_timestamp: string
          id: string
          member_id: number
          session_date: string
          session_type: string
          similarity_score: number
          start_timestamp: string
          status: Database["public"]["Enums"]["parliament_clip_status"]
          thumbnail_url: string
          transcript: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
        }[]
      }
      search_parliament_clips: {
        Args: {
          max_results?: number
          member_filter?: number
          query_embedding: string
          similarity_threshold?: number
        }
        Returns: {
          clip_url: string
          duration_seconds: number
          end_timestamp: string
          id: string
          member_id: number
          session_date: string
          similarity: number
          start_timestamp: string
          transcript: string
        }[]
      }
      search_parliament_clips_by_vector: {
        Args: {
          match_limit?: number
          match_threshold?: number
          query_embedding_text: string
          target_member_id: number
        }
        Returns: {
          clip_url: string
          created_at: string
          description: string
          duration_seconds: number
          end_timestamp: string
          id: string
          member_id: number
          session_date: string
          session_type: string
          session_uid: string
          similarity_score: number
          start_timestamp: string
          status: Database["public"]["Enums"]["parliament_clip_status"]
          thumbnail_url: string
          transcript: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
        }[]
      }
      search_parliament_clips_fulltext: {
        Args: {
          max_results?: number
          member_filter?: number
          search_query: string
        }
        Returns: {
          clip_url: string
          duration_seconds: number
          end_timestamp: string
          id: string
          member_id: number
          rank: number
          session_date: string
          start_timestamp: string
          transcript: string
        }[]
      }
      search_parliament_clips_three_tier: {
        Args: {
          match_limit?: number
          search_query: string
          target_member_id?: number
        }
        Returns: {
          clip_url: string
          created_at: string
          description: string
          duration_seconds: number
          end_timestamp: string
          id: string
          match_tier: number
          member_id: number
          search_rank: number
          session_date: string
          session_type: string
          start_timestamp: string
          status: Database["public"]["Enums"]["parliament_clip_status"]
          thumbnail_url: string
          transcript: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
        }[]
      }
      search_user_clips_by_embedding: {
        Args: {
          match_limit?: number
          match_threshold?: number
          query_embedding_text: string
          target_team_id?: string
          target_user_id?: string
        }
        Returns: {
          clip_id: string
          clip_url: string
          created_at: string
          duration: string
          id: string
          parliament_member_clips: Json
          segments: Json
          session_date: string
          session_type: string
          similarity_score: number
          status: Database["public"]["Enums"]["parliament_clip_status"]
          thumbnail_url: string
          transcript: string
          updated_at: string
          user_id: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
          watermark_position: Database["public"]["Enums"]["watermark_position"]
          watermark_url: string
        }[]
      }
      search_user_clips_by_vector: {
        Args: {
          match_limit?: number
          match_threshold?: number
          query_embedding_text: string
          target_team_id?: string
          target_user_id?: string
        }
        Returns: {
          clip_url: string
          created_at: string
          description: string
          duration_seconds: number
          end_timestamp: string
          id: string
          member_id: number
          member_name: string
          member_party: string
          parliament_clip_id: string
          segments: Json
          session_date: string
          session_type: string
          similarity_score: number
          start_timestamp: string
          status: Database["public"]["Enums"]["parliament_clip_status"]
          team_id: string
          thumbnail_url: string
          title: string
          transcript: string
          user_id: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
        }[]
      }
      search_user_clips_three_tier: {
        Args: {
          match_limit?: number
          search_query: string
          target_team_id?: string
          target_user_id?: string
        }
        Returns: {
          clip_url: string
          created_at: string
          description: string
          duration_seconds: number
          id: string
          match_tier: number
          member_id: number
          search_rank: number
          thumbnail_url: string
          title: string
          transcript: string
          updated_at: string
          user_id: string
          vertical_clip_url: string
          vertical_thumbnail_url: string
        }[]
      }
      show_limit: { Args: never; Returns: number }
      show_trgm: { Args: { "": string }; Returns: string[] }
      text_to_bytea: { Args: { data: string }; Returns: string }
      transfer_team_ownership: {
        Args: {
          p_current_owner_id: string
          p_new_owner_id: string
          p_team_id: string
        }
        Returns: boolean
      }
      trigger_embedding_generation_manually: {
        Args: { clip_id_param: string; table_name_param?: string }
        Returns: string
      }
      trigger_parliament_event_sync_manually: { Args: never; Returns: string }
      trigger_parliament_sync_manually: { Args: never; Returns: string }
      trigger_runpod_processing_manually: {
        Args: {
          endpoint_param?: string
          record_id_param: string
          table_name_param: string
        }
        Returns: string
      }
      trigger_video_sync_manually: {
        Args: { file_name?: string }
        Returns: string
      }
      update_clip_watermark: {
        Args: {
          clip_id: string
          p_watermark_position?: Database["public"]["Enums"]["watermark_position"]
          p_watermark_url?: string
        }
        Returns: boolean
      }
      urlencode:
        | { Args: { data: Json }; Returns: string }
        | {
            Args: { string: string }
            Returns: {
              error: true
            } & "Could not choose the best candidate function between: public.urlencode(string => bytea), public.urlencode(string => varchar). Try renaming the parameters or the function itself in the database so function overloading can be resolved"
          }
        | {
            Args: { string: string }
            Returns: {
              error: true
            } & "Could not choose the best candidate function between: public.urlencode(string => bytea), public.urlencode(string => varchar). Try renaming the parameters or the function itself in the database so function overloading can be resolved"
          }
      user_heartbeat: { Args: { user_uuid: string }; Returns: undefined }
      validate_segments_structure: {
        Args: { segments_data: Json }
        Returns: boolean
      }
      validate_segments_timestamps: {
        Args: { segments_data: Json }
        Returns: boolean
      }
    }
    Enums: {
      app_role: "admin" | "user"
      parliament_clip_status:
        | "processing"
        | "completed"
        | "failed"
        | "pending_review"
      parliament_contact_type:
        | "Parliamentary"
        | "Constituency"
        | "Website"
        | "Social Media"
        | "Email"
        | "Phone"
        | "Address"
        | "Other"
      parliament_division_result: "Passed" | "Rejected" | "Tied" | "NoResult"
      parliament_event_processing_status:
        | "pending"
        | "processing"
        | "processed"
        | "failed"
      parliament_gender: "M" | "F" | "Other" | "Unknown"
      parliament_house: "Commons" | "Lords"
      parliament_sync_status_enum:
        | "pending"
        | "running"
        | "completed"
        | "failed"
      parliament_sync_type:
        | "members"
        | "contacts"
        | "portraits"
        | "voting_history"
        | "cron_trigger"
      parliament_vote_type:
        | "Aye"
        | "No"
        | "DidNotVote"
        | "Abstain"
        | "NoVoteRecorded"
        | "SuspendedOrWithdrawnWhip"
      queue_job_status: "pending" | "running" | "completed" | "failed"
      segment_evaluation_error_reason:
        | "wrong_speaker_detected"
        | "wrong_mp_matched"
      skip_reason_type:
        | "bad_quality"
        | "no_speaker_faces"
        | "already_added_similar_pictures"
      team_role: "owner" | "administrator" | "user"
      watermark_position:
        | "center"
        | "top_left"
        | "top_right"
        | "bottom_left"
        | "bottom_right"
    }
    CompositeTypes: {
      http_header: {
        field: string | null
        value: string | null
      }
      http_request: {
        method: unknown
        uri: string | null
        headers: Database["public"]["CompositeTypes"]["http_header"][] | null
        content_type: string | null
        content: string | null
      }
      http_response: {
        status: number | null
        content_type: string | null
        headers: Database["public"]["CompositeTypes"]["http_header"][] | null
        content: string | null
      }
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      app_role: ["admin", "user"],
      parliament_clip_status: [
        "processing",
        "completed",
        "failed",
        "pending_review",
      ],
      parliament_contact_type: [
        "Parliamentary",
        "Constituency",
        "Website",
        "Social Media",
        "Email",
        "Phone",
        "Address",
        "Other",
      ],
      parliament_division_result: ["Passed", "Rejected", "Tied", "NoResult"],
      parliament_event_processing_status: [
        "pending",
        "processing",
        "processed",
        "failed",
      ],
      parliament_gender: ["M", "F", "Other", "Unknown"],
      parliament_house: ["Commons", "Lords"],
      parliament_sync_status_enum: [
        "pending",
        "running",
        "completed",
        "failed",
      ],
      parliament_sync_type: [
        "members",
        "contacts",
        "portraits",
        "voting_history",
        "cron_trigger",
      ],
      parliament_vote_type: [
        "Aye",
        "No",
        "DidNotVote",
        "Abstain",
        "NoVoteRecorded",
        "SuspendedOrWithdrawnWhip",
      ],
      queue_job_status: ["pending", "running", "completed", "failed"],
      segment_evaluation_error_reason: [
        "wrong_speaker_detected",
        "wrong_mp_matched",
      ],
      skip_reason_type: [
        "bad_quality",
        "no_speaker_faces",
        "already_added_similar_pictures",
      ],
      team_role: ["owner", "administrator", "user"],
      watermark_position: [
        "center",
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right",
      ],
    },
  },
} as const
