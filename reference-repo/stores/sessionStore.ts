"use client";

import { observable } from "@legendapp/state";

type SessionState = {
  fullVideoUrl: string | null;
  sessionDuration: number; // in seconds
  sessionMaxTimestamp: string; // hh:mm:ss.yyy format
  isLoading: boolean;
  error: string | null;
};

// Create the observable store
export const session$ = observable<SessionState>({
  fullVideoUrl: null,
  sessionDuration: 0,
  sessionMaxTimestamp: "00:00:00.000",
  isLoading: false,
  error: null,
});

// Helper function to format seconds to timestamp (hh:mm:ss.yyy)
function formatSecondsToTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${secs.toFixed(3).padStart(6, "0")}`;
}

/**
 * Load video duration from URL by fetching metadata only (not the full video)
 * This only downloads the video headers/metadata (~few KB)
 */
export async function loadSessionDuration(url: string): Promise<number> {
  session$.isLoading.set(true);
  session$.fullVideoUrl.set(url);
  session$.error.set(null);

  return new Promise<number>((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';

    // Guard flag to prevent handlers from executing multiple times
    let handlerExecuted = false;
    let timeoutId: NodeJS.Timeout | null = null;

    // Helper to clean up and remove listeners
    const cleanup = () => {
      // Clear timeout if it exists
      if (timeoutId) clearTimeout(timeoutId);
      // Remove event listeners before clearing src to prevent triggering more events
      video.onloadedmetadata = null;
      video.onerror = null;
      // Now safe to clear src without triggering onerror
      video.src = '';
    };

    // Try without CORS first, then with anonymous if that fails
    video.crossOrigin = null;
    video.src = url;

    const attemptWithCORS = () => {
      // Remove listeners before clearing src
      video.onerror = null;
      video.src = '';

      // Try again with CORS
      video.crossOrigin = 'anonymous';
      video.src = url;

      // Re-attach error handler for CORS attempt
      video.onerror = handleError;
    };

    const handleError = () => {
      // Prevent re-entry
      if (handlerExecuted) return;

      // If first attempt failed and we haven't tried CORS yet, try with CORS
      if (!corsRetryAttempted && video.crossOrigin === null) {
        corsRetryAttempted = true;
        attemptWithCORS();
        return;
      }

      // Mark as executed to prevent infinite loop
      handlerExecuted = true;

      // Both attempts failed - gracefully degrade
      // Set a fallback duration (2 hours = 7200 seconds) for validation to still work
      const fallbackDuration = 7200;
      session$.sessionDuration.set(fallbackDuration);
      session$.sessionMaxTimestamp.set(formatSecondsToTimestamp(fallbackDuration));
      session$.error.set('Could not load exact session duration, using fallback');
      session$.isLoading.set(false);

      // Clean up safely
      cleanup();

      // Resolve with fallback instead of rejecting
      console.warn('Using fallback session duration due to video loading error');
      resolve(fallbackDuration);
    };

    video.onloadedmetadata = () => {
      // Prevent re-entry
      if (handlerExecuted) return;
      handlerExecuted = true;

      const duration = video.duration;

      if (isNaN(duration) || !isFinite(duration)) {
        const error = 'Invalid video duration';
        session$.error.set(error);
        session$.isLoading.set(false);
        cleanup();
        reject(new Error(error));
        return;
      }

      session$.sessionDuration.set(duration);
      session$.sessionMaxTimestamp.set(formatSecondsToTimestamp(duration));
      session$.isLoading.set(false);

      // Clean up safely
      cleanup();

      resolve(duration);
    };

    let corsRetryAttempted = false;

    video.onerror = handleError;

    // Timeout after 10 seconds
    timeoutId = setTimeout(() => {
      // Prevent re-entry
      if (handlerExecuted) return;
      handlerExecuted = true;

      if (session$.isLoading.peek()) {
        // Use fallback on timeout as well
        const fallbackDuration = 7200;
        session$.sessionDuration.set(fallbackDuration);
        session$.sessionMaxTimestamp.set(formatSecondsToTimestamp(fallbackDuration));
        session$.error.set('Timeout loading video metadata, using fallback');
        session$.isLoading.set(false);

        cleanup();

        console.warn('Using fallback session duration due to timeout');
        resolve(fallbackDuration);
      }
    }, 10000);
  });
}

/**
 * Set session duration directly from a value (e.g., from database)
 * This bypasses loading from video URL and sets duration immediately
 */
export function setSessionDuration(duration: number, videoUrl?: string | null): void {
  if (isNaN(duration) || !isFinite(duration) || duration < 0) {
    console.error('Invalid session duration:', duration);
    return;
  }

  session$.sessionDuration.set(duration);
  session$.sessionMaxTimestamp.set(formatSecondsToTimestamp(duration));
  session$.isLoading.set(false);
  session$.error.set(null);
  
  if (videoUrl !== undefined) {
    session$.fullVideoUrl.set(videoUrl);
  }
}

/**
 * Reset session store
 */
export function resetSessionStore() {
  session$.fullVideoUrl.set(null);
  session$.sessionDuration.set(0);
  session$.sessionMaxTimestamp.set("00:00:00.000");
  session$.isLoading.set(false);
  session$.error.set(null);
}
