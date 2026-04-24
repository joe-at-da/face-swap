"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import MyClipsSearchBar from "./components/my-clips-search-bar";
import MyClipsFilters from "./components/my-clips-filters";
import { MyClipsGrid } from "./components/my-clips-grid";
import { toast } from "sonner";
import type { DateRange } from "react-day-picker";
import type { UserClip } from "@/types/user-clips";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import type { RealtimeChannel } from "@supabase/supabase-js";
import { useUser } from "@/stores/hooks/useUser";
import { use$ } from "@legendapp/state/react";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination";

export default function MyClipsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const isInitialMount = useRef(true);
  const urlUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const channelRef = useRef<RealtimeChannel | null>(null);
  const { user: userObservable } = useUser();
  const user = use$(userObservable);

  // Search and filter state - Initialize from URL params on mount
  const initialSearchTerm = searchParams.get("search") || "";
  // Similarity search is disabled, always use text search
  const initialSearchType = "text" as const;
  const hasInitialSearch = !!initialSearchTerm.trim();

  const [clips, setClips] = useState<UserClip[]>([]);
  const [filteredClips, setFilteredClips] = useState<UserClip[]>([]);
  // If there's an initial search, we'll be searching, so start with loading true
  // If no initial search, we'll fetch all clips, so also start with loading true
  const [isLoading, setIsLoading] = useState(true);

  const [searchTerm, setSearchTerm] = useState(initialSearchTerm);
  const searchTermRef = useRef(searchTerm);
  const [searchType, setSearchType] = useState<"text" | "similarity">(initialSearchType);
  const [dateRange, setDateRange] = useState<DateRange>({
    from: undefined,
    to: undefined,
  });
  const [status, setStatus] = useState("all");
  const [sortBy] = useState("created_at");
  const [sortOrder] = useState("desc");

  // Client-side pagination & API fetch sizing
  const ITEMS_PER_PAGE = 12;
  const API_PAGE_SIZE = 100; // fetch enough items per request to cover client pagination
  const [currentPage, setCurrentPage] = useState(1);

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

  // Sync state from URL params when they change (e.g., browser back button)
  useEffect(() => {
    // Skip on initial mount - we already initialized from URL params
    if (!hasInitialized.current) return;

    const urlSearch = searchParams.get("search") || "";
    // Similarity search is disabled, always use text search
    const urlSearchType = "text" as const;

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
        // Base params reused across pages
        const requestParams = new URLSearchParams({
          page: page.toString(),
          limit: API_PAGE_SIZE.toString(),
          sortBy,
          sortOrder,
        });

        // Add optional filters
        if (status !== "all") {
          requestParams.append("status", status);
        }
        if (dateRange.from) {
          requestParams.append("dateFrom", dateRange.from.toISOString());
        }
        if (dateRange.to) {
          requestParams.append("dateTo", dateRange.to.toISOString());
        }

        // Fetch all pages to support client-side pagination
        let currentPageToFetch = page;
        let totalPagesFromApi = 1;
        const allClips: UserClip[] = [];

        do {
          requestParams.set("page", currentPageToFetch.toString());

          const response = await fetch(`/api/user-clips?${requestParams}`);
          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error || "Failed to fetch clips");
          }

          if (Array.isArray(data.data)) {
            allClips.push(...data.data);
          }

          // Read pagination info from API to know if more pages exist
          totalPagesFromApi = data.pagination?.totalPages ?? 1;
          currentPageToFetch += 1;
        } while (currentPageToFetch <= totalPagesFromApi);

        setClips(allClips);
      } catch (error) {
        console.error("Error fetching clips:", error);
        toast.error("Failed to load clips");
        setClips([]);
      } finally {
        setIsLoading(false);
      }
    },
    [status, dateRange, sortBy, sortOrder]
  );

  // Filter clips based on search
  const filterClips = useCallback(async () => {
    if (!searchTerm.trim()) {
      setFilteredClips(clips);
      setIsLoading(false);
      return;
    }

    // Keep loading state true during search
    setIsLoading(true);
    // Don't clear filteredClips immediately - keep showing previous results or loading state

    try {
      if (searchType === "text") {
        // Use the API endpoint for text search to utilize the server-side search logic
        try {
          const searchParams = new URLSearchParams({
            page: "1",
            limit: "50",
            search: searchTerm,
            sortBy: "created_at",
            sortOrder: "desc",
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
        // API call for similarity search
        try {
          const teamIdParam = searchParams.get("teamId");
          const body: { query: string; limit: number; teamId?: string } = {
            query: searchTerm,
            limit: 50,
          };
          if (teamIdParam) {
            body.teamId = teamIdParam;
          }

          const response = await fetch("/api/user-clips/search", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
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
            // Fall back to empty results
            setFilteredClips([]);
          }
        } catch (error) {
          console.error("Similarity search error:", error);
          // Fall back to empty results
          setFilteredClips([]);
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [clips, searchTerm, searchType, searchParams]);

  // Track if initial mount has completed
  const hasInitialized = useRef(false);
  const hasInitialSearchRef = useRef(hasInitialSearch);

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
  }, [filterClips, searchTerm, searchType]);

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

  // Reset to page 1 when filters or search change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, dateRange, status]);

  // Calculate pagination values
  const totalPages = Math.ceil(filteredClips.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedClips = filteredClips.slice(startIndex, endIndex);

  // Ensure currentPage doesn't exceed totalPages
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(1);
    }
  }, [totalPages, currentPage]);

  // Subscribe to Supabase realtime updates for personal clips
  useEffect(() => {
    if (!user?.id) return;

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

        // Create channel with filter for personal clips (user_id matches and team_id is null)
        const channel = supabase
          .channel(`user-clips-personal-${user.id}`)
          .on(
            "postgres_changes",
            {
              event: "INSERT",
              schema: "public",
              table: "user_clips",
              filter: `user_id=eq.${user.id}`,
            },
            async (payload) => {
              // Only process if team_id is null (personal clip)
              if (payload.new && !payload.new.team_id && !payload.new.is_deleted) {
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
              filter: `user_id=eq.${user.id}`,
            },
            async (payload) => {
              if (!payload.new) return;

              // If clip was deleted or assigned to a team, remove it from personal clips list
              if (payload.new.is_deleted || payload.new.team_id) {
                setClips((prevClips) =>
                  prevClips.filter((clip) => clip.id !== payload.new.id)
                );
                setFilteredClips((prevClips) =>
                  prevClips.filter((clip) => clip.id !== payload.new.id)
                );
                return;
              }

              // Only process if team_id is null (personal clip)
              if (!payload.new.team_id) {
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
                        toast.success("Your clip is ready!");
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
              filter: `user_id=eq.${user.id}`,
            },
            (payload) => {
              // Remove deleted clip from the list
              setClips((prevClips) =>
                prevClips.filter((clip) => clip.id !== payload.old.id)
              );
              setFilteredClips((prevClips) =>
                prevClips.filter((clip) => clip.id !== payload.old.id)
              );
            }
          )
          .subscribe();

        channelRef.current = channel;
      } catch (error) {
        console.error("Error setting up realtime subscription:", error);
      }
    };

    setupRealtime();

    // Cleanup subscription on unmount or when user changes
    return () => {
      if (channelRef.current) {
        const supabase = createSupabaseBrowserClient();
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [user?.id]);

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

      return Promise.resolve();
    } catch (error) {
      console.error("Error deleting clip:", error);
      return Promise.reject(error);
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h1 className="text-2xl font-bold text-foreground tracking-tight pt-4" style={{ fontFamily: 'var(--font-family-sans, Inter)' }}>
          My Clips
        </h1>
        <h2 className="text-muted-foreground">
          Manage and organize your parliamentary video clips. Track processing
          status and share your content.
        </h2>
        <h3 className="text-lg font-bold text-foreground pt-2 pb-1">Search for exact words or phrases in the transcript</h3>
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
      {(filteredClips.length > 0 || clips.length > 0) && (
        <div className="flex items-center justify-end">
          <p className="text-base md:text-sm text-muted-foreground">
            Showing {filteredClips.length} of {clips.length} clips
            {searchTerm && <span> for &ldquo;{searchTerm}&rdquo;</span>}
          </p>
        </div>
      )}

      <MyClipsGrid
        clips={paginatedClips}
        isLoading={isLoading}
        onDeleteClip={handleDeleteClip}
        searchTerm={searchTerm}
      />

      {/* Pagination Controls */}
      {filteredClips.length > 0 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  if (currentPage > 1) {
                    setCurrentPage(currentPage - 1);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }
                }}
                className={`[&>span]:hidden ${currentPage === 1 ? "pointer-events-none opacity-50" : ""}`}
              />
            </PaginationItem>

            {/* Page Numbers */}
            {(() => {
              const pages: (number | 'ellipsis')[] = [];
              const showEllipsis = totalPages > 7;

              if (!showEllipsis) {
                // Show all pages if 7 or fewer
                for (let i = 1; i <= totalPages; i++) {
                  pages.push(i);
                }
              } else {
                // Always show first page
                pages.push(1);

                if (currentPage <= 4) {
                  // Near the start: 1 2 3 4 5 ... last
                  for (let i = 2; i <= 5; i++) {
                    pages.push(i);
                  }
                  pages.push('ellipsis');
                  pages.push(totalPages);
                } else if (currentPage >= totalPages - 3) {
                  // Near the end: 1 ... (n-4) (n-3) (n-2) (n-1) n
                  pages.push('ellipsis');
                  for (let i = totalPages - 4; i <= totalPages; i++) {
                    pages.push(i);
                  }
                } else {
                  // In the middle: 1 ... (current-1) current (current+1) ... last
                  pages.push('ellipsis');
                  for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                    pages.push(i);
                  }
                  pages.push('ellipsis');
                  pages.push(totalPages);
                }
              }

              return pages.map((item, index) => {
                if (item === 'ellipsis') {
                  return (
                    <PaginationItem key={`ellipsis-${index}`}>
                      <PaginationEllipsis />
                    </PaginationItem>
                  );
                }
                return (
                  <PaginationItem key={item}>
                    <PaginationLink
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        setCurrentPage(item);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      isActive={currentPage === item}
                      className={
                        currentPage === item
                          ? "border-0 shadow-none text-foreground hover:text-foreground hover:bg-transparent"
                          : "text-muted-foreground hover:text-foreground"
                      }
                    >
                      {item}
                    </PaginationLink>
                  </PaginationItem>
                );
              });
            })()}

            <PaginationItem>
              <PaginationNext
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  if (currentPage < totalPages) {
                    setCurrentPage(currentPage + 1);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }
                }}
                className={`[&>span]:hidden ${currentPage === totalPages ? "pointer-events-none opacity-50" : ""}`}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  );
}
