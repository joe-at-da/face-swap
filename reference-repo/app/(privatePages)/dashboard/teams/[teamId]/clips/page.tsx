"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import MyClipsSearchBar from "@/app/(privatePages)/dashboard/my-clips/components/my-clips-search-bar";
import MyClipsFilters from "@/app/(privatePages)/dashboard/my-clips/components/my-clips-filters";
import { MyClipsGrid } from "@/app/(privatePages)/dashboard/my-clips/components/my-clips-grid";
import { toast } from "sonner";
import type { DateRange } from "react-day-picker";
import type { UserClip, PaginationInfo } from "@/types/user-clips";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import type { RealtimeChannel } from "@supabase/supabase-js";

export default function TeamClipsPage() {
  const params = useParams();
  const teamId = params.teamId as string;
  const searchParams = useSearchParams();
  const router = useRouter();
  const isInitialMount = useRef(true);
  const urlUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const channelRef = useRef<RealtimeChannel | null>(null);

  // Search and filter state - Initialize from URL params on mount
  const initialSearchTerm = searchParams.get("search") || "";
  const initialSearchType = searchParams.get("type") === "similarity" ? "similarity" : "text";
  const hasInitialSearch = !!initialSearchTerm.trim();

  const [clips, setClips] = useState<UserClip[]>([]);
  const [filteredClips, setFilteredClips] = useState<UserClip[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pagination, setPagination] = useState<PaginationInfo>({
    currentPage: 1,
    totalPages: 0,
    totalItems: 0,
    hasNextPage: false,
    hasPreviousPage: false,
    itemsPerPage: 20,
  });

  const [searchTerm, setSearchTerm] = useState(initialSearchTerm);
  const searchTermRef = useRef(initialSearchTerm);
  const [searchType, setSearchType] = useState<"text" | "similarity">(initialSearchType);
  const [dateRange, setDateRange] = useState<DateRange>({
    from: undefined,
    to: undefined,
  });
  const [status, setStatus] = useState("all");
  const [sortBy] = useState("created_at");
  const [sortOrder] = useState("desc");

  // Update URL with search parameters
  const updateURL = useCallback((term: string, type: "text" | "similarity") => {
    const params = new URLSearchParams(searchParams.toString());
    
    if (term.trim()) {
      params.set("search", term);
    } else {
      params.delete("search");
    }
    
    if (type === "similarity") {
      params.set("type", "similarity");
    } else {
      params.delete("type");
    }
    
    const newUrl = params.toString() 
      ? `${window.location.pathname}?${params.toString()}`
      : window.location.pathname;
    
    router.replace(newUrl, { scroll: false });
  }, [searchParams, router]);

  // Track if initial mount has completed
  const hasInitialized = useRef(false);
  const hasInitialSearchRef = useRef(hasInitialSearch);

  // Sync state from URL params when they change (e.g., browser back button)
  useEffect(() => {
    // Skip on initial mount - we already initialized from URL params
    if (!hasInitialized.current) return;

    const urlSearch = searchParams.get("search") || "";
    const urlType = searchParams.get("type");
    const urlSearchType: "text" | "similarity" = urlType === "similarity" ? "similarity" : "text";

    // Only update state if URL params differ from current state
    if (urlSearch !== searchTerm || urlSearchType !== searchType) {
      setSearchTerm(urlSearch);
      setSearchType(urlSearchType);
      // Mark as not initial mount to allow URL updates after sync
      isInitialMount.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Update URL when searchTerm changes (debounced)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // Clear existing timeout
    if (urlUpdateTimeoutRef.current) {
      clearTimeout(urlUpdateTimeoutRef.current);
    }

    // Set new timeout for debounced URL update
    urlUpdateTimeoutRef.current = setTimeout(() => {
      updateURL(searchTerm, searchType);
    }, 500);

    return () => {
      if (urlUpdateTimeoutRef.current) {
        clearTimeout(urlUpdateTimeoutRef.current);
      }
    };
  }, [searchTerm, searchType, updateURL]);

  const fetchClips = useCallback(
    async (page = 1) => {
      setIsLoading(true);

      try {
        // Build search params for API call
        const searchParams = new URLSearchParams({
          page: page.toString(),
          limit: "20",
          sortBy,
          sortOrder,
          teamId, // Add teamId to filter for team clips
        });

        // Add optional filters
        if (status !== "all") {
          searchParams.append("status", status);
        }
        if (dateRange.from) {
          searchParams.append("dateFrom", dateRange.from.toISOString());
        }
        if (dateRange.to) {
          searchParams.append("dateTo", dateRange.to.toISOString());
        }

        const response = await fetch(`/api/user-clips?${searchParams}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch team clips");
        }

        setClips(data.data || []);
        setPagination(data.pagination);
      } catch (error) {
        console.error("Error fetching team clips:", error);
        toast.error("Failed to load team clips");
        setClips([]);
      } finally {
        setIsLoading(false);
      }
    },
    [teamId, status, dateRange, sortBy, sortOrder]
  );

  // Filter clips based on search
  const filterClips = useCallback(async () => {
    if (!searchTerm.trim()) {
      setFilteredClips(clips);
      return;
    }

    setIsLoading(true);

    try {
      if (searchType === "text") {
        try {
          const searchParams = new URLSearchParams({
            page: "1",
            limit: "50",
            search: searchTerm,
            sortBy: "created_at",
            sortOrder: "desc",
            teamId,
          });

          const response = await fetch(`/api/user-clips?${searchParams}`);
          const data = await response.json();

          if (response.ok) {
            setFilteredClips(data.data || []);
          } else {
            console.error("Text search failed:", data.error);
            setFilteredClips([]);
          }
        } catch (error) {
          console.error("Text search error:", error);
          setFilteredClips([]);
        }
      } else if (searchType === "similarity") {
        try {
          const response = await fetch("/api/user-clips/search", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              query: searchTerm,
              limit: 50,
              teamId,
            }),
          });

          if (response.ok) {
            const result = await response.json();
            // Sort by similarity_score DESC to show highest similarity first
            const sortedClips = (result.clips || []).sort((a: UserClip & { similarity_score?: number }, b: UserClip & { similarity_score?: number }) => {
              const scoreA = a.similarity_score ?? 0;
              const scoreB = b.similarity_score ?? 0;
              return scoreB - scoreA; // Descending order
            });
            setFilteredClips(sortedClips);
          } else {
            console.error("Similarity search failed");
            setFilteredClips([]);
          }
        } catch (error) {
          console.error("Similarity search error:", error);
          setFilteredClips([]);
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [clips, searchTerm, searchType, teamId]);

  // Initial load effect - run search immediately if URL has search params, otherwise fetch clips
  useEffect(() => {
    if (hasInitialized.current) return;
    
    // Mark as initialized immediately to prevent other effects from running
    hasInitialized.current = true;
    
    if (hasInitialSearchRef.current) {
      // If there's a search in URL, run search immediately (no debounce)
      filterClips();
    } else {
      // Otherwise, fetch all clips
      fetchClips(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount - filterClips and fetchClips are stable callbacks

  // Debounced search effect (for subsequent changes after initial load)
  useEffect(() => {
    // Skip on initial mount - handled by the effect above
    if (!hasInitialized.current) return;

    // For subsequent changes, use debounce
    const timer = setTimeout(() => {
      filterClips();
    }, 500);

    return () => clearTimeout(timer);
  }, [filterClips]);

  // Effect to fetch clips when filters change (only after initial load)
  useEffect(() => {
    // Skip on initial mount - handled by the effect above
    if (!hasInitialized.current) return;
    
    // Only fetch if there's no search term (search is handled by filterClips)
    if (!searchTerm.trim()) {
      fetchClips(1);
    }
  }, [fetchClips, status, dateRange, searchTerm]);

  // Keep searchTerm ref updated
  useEffect(() => {
    searchTermRef.current = searchTerm;
  }, [searchTerm]);

  // Effect to set filtered clips (only when not searching and clips change)
  useEffect(() => {
    if (!searchTerm.trim() && clips.length > 0) {
      setFilteredClips(clips);
    }
  }, [clips, searchTerm]);

  // Subscribe to Supabase realtime updates for team clips
  useEffect(() => {
    if (!teamId) return;

    const supabase = createSupabaseBrowserClient();

    const setupRealtime = async () => {
      try {
        const {
          data: { session },
          error: authError,
        } = await supabase.auth.getSession();

        if (authError || !session) {
          return;
        }

        // Set auth token for realtime before subscribing
        await supabase.realtime.setAuth(session.access_token);

        // Create channel with filter for team clips (team_id matches)
        const channel = supabase
          .channel(`team-clips-${teamId}`)
          .on(
            "postgres_changes",
            {
              event: "INSERT",
              schema: "public",
              table: "user_clips",
              filter: `team_id=eq.${teamId}`,
            },
            async (payload) => {
              // Only process if team_id matches and not deleted
              if (payload.new && payload.new.team_id === teamId && !payload.new.is_deleted) {
                // Fetch the full clip with relations from API
                try {
                  const response = await fetch(`/api/user-clips/${payload.new.id}`);
                  if (response.ok) {
                    const data = await response.json();
                    const newClip = data.data as UserClip;
                    // Add new clip to the beginning of the list (most recent first)
                    setClips((prevClips) => {
                      // Check if clip already exists to avoid duplicates
                      if (prevClips.some((clip) => clip.id === newClip.id)) {
                        return prevClips;
                      }
                      return [newClip, ...prevClips];
                    });
                    // Update filtered clips if not searching
                    if (!searchTermRef.current.trim()) {
                      setFilteredClips((prevClips) => {
                        if (prevClips.some((clip) => clip.id === newClip.id)) {
                          return prevClips;
                        }
                        return [newClip, ...prevClips];
                      });
                      // Update pagination
                      setPagination((prev) => ({
                        ...prev,
                        totalItems: prev.totalItems + 1,
                      }));
                    }
                  }
                } catch (error) {
                  console.error("Error fetching new clip:", error);
                }
              }
            }
          )
          .on(
            "postgres_changes",
            {
              event: "UPDATE",
              schema: "public",
              table: "user_clips",
              filter: `team_id=eq.${teamId}`,
            },
            async (payload) => {
              if (!payload.new) return;

              // If clip was deleted, team_id changed, or removed from team, remove it from the list
              if (
                payload.new.is_deleted ||
                payload.new.team_id !== teamId ||
                (payload.old?.team_id === teamId && payload.new.team_id !== teamId)
              ) {
                setClips((prevClips) =>
                  prevClips.filter((clip) => clip.id !== payload.new.id)
                );
                setFilteredClips((prevClips) =>
                  prevClips.filter((clip) => clip.id !== payload.new.id)
                );
                setPagination((prev) => ({
                  ...prev,
                  totalItems: Math.max(0, prev.totalItems - 1),
                }));
                return;
              }

              // Only process if team_id still matches
              if (payload.new.team_id === teamId) {
                // Fetch updated clip with relations from API
                try {
                  const response = await fetch(`/api/user-clips/${payload.new.id}`);
                  if (response.ok) {
                    const data = await response.json();
                    const updatedClip = data.data as UserClip;
                    // Update clip in the list
                    setClips((prevClips) =>
                      prevClips.map((clip) =>
                        clip.id === updatedClip.id ? updatedClip : clip
                      )
                    );
                    // Update filtered clips if not searching
                    if (!searchTermRef.current.trim()) {
                      setFilteredClips((prevClips) =>
                        prevClips.map((clip) =>
                          clip.id === updatedClip.id ? updatedClip : clip
                        )
                      );
                    }
                    // Show toast notifications for status changes
                    if (payload.old?.status !== payload.new.status) {
                      if (payload.new.status === "completed") {
                        toast.success("Team clip is ready!");
                      } else if (payload.new.status === "failed") {
                        toast.error("Clip processing failed");
                      }
                    }
                  }
                } catch (error) {
                  console.error("Error fetching updated clip:", error);
                }
              }
            }
          )
          .on(
            "postgres_changes",
            {
              event: "DELETE",
              schema: "public",
              table: "user_clips",
              filter: `team_id=eq.${teamId}`,
            },
            (payload) => {
              // Remove deleted clip from the list
              setClips((prevClips) =>
                prevClips.filter((clip) => clip.id !== payload.old.id)
              );
              setFilteredClips((prevClips) =>
                prevClips.filter((clip) => clip.id !== payload.old.id)
              );
              setPagination((prev) => ({
                ...prev,
                totalItems: Math.max(0, prev.totalItems - 1),
              }));
            }
          )
          .subscribe();

        channelRef.current = channel;
      } catch (error) {
        console.error("Error setting up realtime subscription:", error);
      }
    };

    setupRealtime();

    // Cleanup subscription on unmount or when teamId changes
    return () => {
      if (channelRef.current) {
        const supabase = createSupabaseBrowserClient();
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [teamId]);

  const handleDeleteClip = async (clipId: string) => {
    try {
      const response = await fetch(`/api/user-clips/${clipId}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to delete clip");
      }

      // Remove clip from local state
      setClips((prevClips) => prevClips.filter((clip) => clip.id !== clipId));
      setFilteredClips((prevClips) =>
        prevClips.filter((clip) => clip.id !== clipId)
      );
      setPagination((prev) => ({
        ...prev,
        totalItems: prev.totalItems - 1,
      }));

      return Promise.resolve();
    } catch (error) {
      console.error("Error deleting clip:", error);
      return Promise.reject(error);
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold text-foreground">Team Clips</h1>
        <p className="text-lg text-muted-foreground">
          View and manage clips created by your team. All clips here belong to
          the team and are accessible to all members.
        </p>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <MyClipsSearchBar
          searchTerm={searchTerm}
          onSearchTermChange={setSearchTerm}
          isLoading={isLoading}
        />

        <MyClipsFilters
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
          status={status}
          onStatusChange={setStatus}
        />
      </div>

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-base md:text-sm text-muted-foreground">
          Showing {filteredClips.length} of {clips.length} team clips
          {searchTerm && <span> for &ldquo;{searchTerm}&rdquo;</span>}
        </p>
      </div>

      <MyClipsGrid
        clips={filteredClips}
        isLoading={isLoading}
        onDeleteClip={handleDeleteClip}
        teamId={teamId}
        searchTerm={searchTerm}
      />

      {/* Pagination would go here if needed */}
      {pagination.totalPages > 1 && (
        <div className="flex justify-center mt-8">
          <div className="text-sm text-muted-foreground">
            Showing page {pagination.currentPage} of {pagination.totalPages}
          </div>
        </div>
      )}
    </div>
  );
}
