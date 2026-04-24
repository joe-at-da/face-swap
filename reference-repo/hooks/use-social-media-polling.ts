"use client";

import { useState, useEffect, useCallback } from "react";
import { getUserConnectSocialMediaAccountsActions } from "@/app/actions/postizActions";

export interface ConnectedPlatform {
  name: string;
  identifier: string;
  isConnected: boolean;
  integrationId?: string;
  profile?: string;
  profileName?: string;
  picture?: string;
  toolTip?: string;
  /** For Facebook: true means OAuth complete but page not selected yet */
  inBetweenSteps?: boolean;
}

interface UseSocialMediaPollingReturn {
  platforms: ConnectedPlatform[];
  isLoading: boolean;
  error: string | null;
  postizNotSetup: boolean;
  refetch: () => Promise<void>;
}

interface UseSocialMediaPollingOptions {
  /**
   * Polling interval in milliseconds
   * @default 10000 (10 seconds)
   */
  pollingInterval?: number;
  /**
   * Whether to start polling immediately
   * @default true
   */
  enabled?: boolean;
  /**
   * Whether to pause polling when tab is not visible
   * @default true
   */
  pauseWhenHidden?: boolean;
}

/**
 * Custom hook to poll for social media connection status
 *
 * @param options - Configuration options for polling behavior
 * @returns Object containing platforms data, loading state, error, and refetch function
 *
 * @example
 * ```tsx
 * const { platforms, isLoading, error, refetch } = useSocialMediaPolling({
 *   pollingInterval: 10000,
 *   enabled: true
 * });
 * ```
 */
export function useSocialMediaPolling(
  options: UseSocialMediaPollingOptions = {}
): UseSocialMediaPollingReturn {
  const {
    pollingInterval = 10000,
    enabled = true,
    pauseWhenHidden = true,
  } = options;

  const [platforms, setPlatforms] = useState<ConnectedPlatform[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [postizNotSetup, setPostizNotSetup] = useState(false);

  /**
   * Fetch social media connection status
   */
  const fetchPlatforms = useCallback(async () => {
    try {
      const response = await getUserConnectSocialMediaAccountsActions();

      // Check if Postiz account is not setup yet
      if ("postizNotSetup" in response && response.postizNotSetup) {
        setPostizNotSetup(true);
        // Use response.data if available (may contain Bluesky even without Postiz)
        setPlatforms(response.data || []);
        setError(null);
        return;
      }

      if (response.error) {
        setError(response.error);
        setPlatforms([]);
        setPostizNotSetup(false);
        return;
      }

      if (response.data) {
        setPlatforms(response.data);
        setError(null);
        setPostizNotSetup(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch platforms");
      setPlatforms([]);
      setPostizNotSetup(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Manual refetch function
   */
  const refetch = useCallback(async () => {
    setIsLoading(true);
    await fetchPlatforms();
  }, [fetchPlatforms]);

  /**
   * Set up polling interval
   */
  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Initial fetch
    fetchPlatforms();

    // Set up polling interval
    const intervalId = setInterval(() => {
      // Skip polling if tab is hidden and pauseWhenHidden is enabled
      if (pauseWhenHidden && document.hidden) {
        return;
      }

      fetchPlatforms();
    }, pollingInterval);

    // Clean up interval on unmount
    return () => {
      clearInterval(intervalId);
    };
  }, [enabled, pollingInterval, pauseWhenHidden, fetchPlatforms]);

  /**
   * Resume polling when tab becomes visible (if pauseWhenHidden is enabled)
   */
  useEffect(() => {
    if (!enabled || !pauseWhenHidden) {
      return;
    }

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Fetch immediately when tab becomes visible
        fetchPlatforms();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enabled, pauseWhenHidden, fetchPlatforms]);

  return {
    platforms,
    isLoading,
    error,
    postizNotSetup,
    refetch,
  };
}
