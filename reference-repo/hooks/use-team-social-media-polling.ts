"use client";

import { useState, useEffect, useCallback } from "react";
import { getTeamOwnerSocialMediaAccountsAction } from "@/app/actions/teamPostizActions";

export interface ConnectedPlatform {
  name: string;
  identifier: string;
  isConnected: boolean;
  integrationId?: string;
  profile?: string;
  profileName?: string;
  picture?: string;
  toolTip?: string;
}

interface UseTeamSocialMediaPollingReturn {
  platforms: ConnectedPlatform[];
  isLoading: boolean;
  error: string | null;
  postizNotSetup: boolean;
  ownerName: string | null;
  refetch: () => Promise<void>;
}

interface UseTeamSocialMediaPollingOptions {
  /**
   * Team ID to get owner's social accounts for
   */
  teamId: string;
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
 * Custom hook to poll for team owner's social media connection status
 *
 * @param options - Configuration options for polling behavior
 * @returns Object containing platforms data, loading state, error, owner name, and refetch function
 *
 * @example
 * ```tsx
 * const { platforms, isLoading, error, ownerName, refetch } = useTeamSocialMediaPolling({
 *   teamId: '123-456',
 *   pollingInterval: 10000,
 *   enabled: true
 * });
 * ```
 */
export function useTeamSocialMediaPolling(
  options: UseTeamSocialMediaPollingOptions
): UseTeamSocialMediaPollingReturn {
  const {
    teamId,
    pollingInterval = 10000,
    enabled = true,
    pauseWhenHidden = true,
  } = options;

  const [platforms, setPlatforms] = useState<ConnectedPlatform[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [postizNotSetup, setPostizNotSetup] = useState(false);
  const [ownerName, setOwnerName] = useState<string | null>(null);

  /**
   * Fetch team owner's social media connection status
   */
  const fetchPlatforms = useCallback(async () => {
    try {
      const response = await getTeamOwnerSocialMediaAccountsAction(teamId);

      // Check if Postiz account is not setup yet for team owner
      if ("postizNotSetup" in response && response.postizNotSetup) {
        setPostizNotSetup(true);
        // Use response.data if available (may contain Bluesky even without Postiz)
        setPlatforms(response.data || []);
        setError(null);
        setOwnerName(response.ownerName || null);
        return;
      }

      if (response.error) {
        setError(response.error);
        setPlatforms([]);
        setPostizNotSetup(false);
        setOwnerName(null);
        return;
      }

      if (response.data) {
        setPlatforms(response.data);
        setError(null);
        setPostizNotSetup(false);
        setOwnerName(response.ownerName || null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch platforms");
      setPlatforms([]);
      setPostizNotSetup(false);
      setOwnerName(null);
    } finally {
      setIsLoading(false);
    }
  }, [teamId]);

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
    ownerName,
    refetch,
  };
}
