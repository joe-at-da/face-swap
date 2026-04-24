import { useEffect, useRef } from "react";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { RealtimeChannel } from "@supabase/supabase-js";

interface UserClipData {
  id: string;
  created_at: string;
  updated_at: string;
  status: string;
  duration: string | null;
  segments: Array<{
    start_timestamp: string;
    end_timestamp: string;
  }>;
  transcript: string | null;
  clip_url: string | null;
  vertical_clip_url: string | null;
  thumbnail_url: string | null;
  vertical_thumbnail_url: string | null;
  watermark_url: string | null;
  watermark_position: string | null;
  error_message: string | null;
}

interface UseUserClipRealtimeOptions {
  clipId: string;
  onUpdate: (clip: Partial<UserClipData>) => void;
  enabled?: boolean;
}

/**
 * Hook to subscribe to realtime updates for a specific user clip
 * Automatically handles subscription lifecycle and cleanup
 */
export function useUserClipRealtime({
  clipId,
  onUpdate,
  enabled = true,
}: UseUserClipRealtimeOptions) {
  // Use ref to store the latest onUpdate callback without causing re-subscriptions
  const onUpdateRef = useRef(onUpdate);

  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  useEffect(() => {
    if (!enabled || !clipId) return;

    const supabase = createSupabaseBrowserClient();
    let channel: RealtimeChannel;

    const setupRealtimeSubscription = async () => {
      // Create channel for this specific clip
      channel = supabase.channel(`user-clip-${clipId}`);

      // Subscribe to UPDATE events on user_clips table for this specific clip
      channel
        .on(
          "postgres_changes",
          {
            event: "UPDATE",
            schema: "public",
            table: "user_clips",
            filter: `id=eq.${clipId}`,
          },
          (payload) => {
            console.log("Realtime update received:", payload);
            // Call the update callback with the new data using the ref
            if (payload.new) {
              onUpdateRef.current(payload.new as Partial<UserClipData>);
            }
          }
        )
        .subscribe((status) => {
          console.log(`Realtime subscription status: ${status}`);
        });
    };

    setupRealtimeSubscription();

    // Cleanup subscription on unmount
    return () => {
      if (channel) {
        console.log("Unsubscribing from realtime channel");
        supabase.removeChannel(channel);
      }
    };
  }, [clipId, enabled]); // Removed onUpdate from dependencies
}
