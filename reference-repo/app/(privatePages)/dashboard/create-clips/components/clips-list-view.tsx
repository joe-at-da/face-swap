"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import ClipsSearchBar from "./clips-search-bar";
import ClipsFilters from "./clips-filters";
import ClipCard from "./clip-card";
import SearchLoadingState from "./search-loading-state";
import AllClipsPagination from "@/app/(privatePages)/dashboard/all-clips/components/all-clips-pagination";
import { SmartAvatar } from "@/components/smart-avatar";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { DateRange } from "react-day-picker";
import { Users, Users2, MapPin } from "lucide-react";
import type {
  ParliamentMemberClip,
  ParliamentMember,
} from "@/types/parliament";
import type { Team } from "@/types/teams";

interface ClipsListViewProps {
  mp: ParliamentMember;
  memberId: number;
  team?: Team;
  teamId?: string;
}

const ITEMS_PER_PAGE = 12;

export default function ClipsListView({
  mp,
  memberId,
  team,
  teamId,
}: ClipsListViewProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const isFirstFetch = useRef(true);
  const hasUrlSynced = useRef(false);

  const initialSearchTerm = searchParams.get("search") || "";
  const initialSearchType =
    searchParams.get("searchType") === "hybrid" ? "hybrid" : "text";

  const [clips, setClips] = useState<ParliamentMemberClip[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState(initialSearchTerm);
  const [searchType, setSearchType] = useState<"text" | "hybrid">(initialSearchType);
  const [searchMeta, setSearchMeta] = useState<{
    searchType?: string;
    reranked?: boolean;
  } | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>({
    from: undefined,
    to: undefined,
  });

  const fetchClips = useCallback(
    async (page: number) => {
      setIsLoading(true);
      setHasError(false);
      setErrorMessage(null);
      try {
        const offset = (page - 1) * ITEMS_PER_PAGE;
        const body: Record<string, unknown> = {
          memberId,
          limit: ITEMS_PER_PAGE,
          offset,
          searchType,
          ...(teamId && { teamId }),
        };

        if (searchTerm.trim()) {
          body.query = searchTerm.trim();
        }
        if (dateRange.from) {
          body.dateFrom = dateRange.from.toISOString().split("T")[0];
        }
        if (dateRange.to) {
          body.dateTo = dateRange.to.toISOString().split("T")[0];
        }

        const res = await fetch("/api/clips/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (res.ok) {
          const data = await res.json();
          setClips(data.clips || []);
          setTotal(data.total || 0);
          setSearchMeta(
            data.searchType && data.searchType !== "browse"
              ? { searchType: data.searchType }
              : null
          );
        } else {
          const errorData = await res.json().catch(() => ({}));
          setErrorMessage(errorData.error || "Something went wrong loading clips.");
          setClips([]);
          setTotal(0);
          setHasError(true);
          setSearchMeta(null);
        }
      } catch {
        setErrorMessage("Something went wrong loading clips.");
        setClips([]);
        setTotal(0);
        setHasError(true);
        setSearchMeta(null);
      } finally {
        setIsLoading(false);
      }
    },
    [memberId, searchTerm, searchType, dateRange, teamId]
  );

  // Fetch on mount and when filters/search change (debounced)
  useEffect(() => {
    const delay = isFirstFetch.current ? 0 : 500;
    isFirstFetch.current = false;

    const timer = setTimeout(() => {
      setCurrentPage(1);
      fetchClips(1);
    }, delay);

    return () => clearTimeout(timer);
  }, [fetchClips]);

  // URL sync (debounced, skips initial mount)
  useEffect(() => {
    if (!hasUrlSynced.current) {
      hasUrlSynced.current = true;
      return;
    }

    const timer = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString());
      if (searchTerm.trim()) {
        params.set("search", searchTerm);
      } else {
        params.delete("search");
      }
      if (searchType === "hybrid") {
        params.set("searchType", searchType);
      } else {
        params.delete("searchType");
      }
      const newUrl = params.toString()
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;
      router.replace(newUrl, { scroll: false });
    }, 500);

    return () => clearTimeout(timer);
  }, [searchTerm, searchType, searchParams, router]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    fetchClips(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Get primary portrait URL
  const primaryPortrait = mp.parliament_member_portraits?.find(
    (p) => p.is_primary
  )?.image_url;

  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
  const displayStart = total > 0 ? (currentPage - 1) * ITEMS_PER_PAGE + 1 : 0;
  const displayEnd = Math.min(currentPage * ITEMS_PER_PAGE, total);

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="space-y-4">
        <div className="space-y-3">
          <h1 className="text-2xl font-bold text-foreground pt-4">
            Speech Library
          </h1>
          {team && (
            <p className="text-muted-foreground">
              Creating clips for {team.name} - These clips will belong to the team and persist even if you leave.
            </p>
          )}
        </div>

        {/* Team Info Badge (if creating for team) */}
        {team && (
          <div className="flex items-center gap-2 p-3 bg-primary/10 border border-primary/20 rounded-lg">
            <Users className="h-5 w-5 text-primary" />
            <div>
              <p className="font-semibold text-primary">Team: {team.name}</p>
              {team.description && (
                <p className="text-sm text-muted-foreground">
                  {team.description}
                </p>
              )}
            </div>
          </div>
        )}

        {/* MP Info Card */}
        <div className="pb-6 border-b border-border">
          <div className="flex items-center gap-4">
            <SmartAvatar
              profileImage={primaryPortrait}
              firstName={mp.display_name?.split(" ")[0]}
              lastName={mp.display_name?.split(" ").slice(1).join(" ")}
              className="h-16 w-16"
            />
            <div className="space-y-1">
              <h2 className="text-sm font-semibold font-sans">
                {mp.display_name}
              </h2>
              <p className="text-sm font-normal text-foreground flex items-center gap-2">
                <span className="bg-muted rounded p-1">
                  <Users2 className="h-4 w-4" />
                </span>
                {mp.party_name || mp.party_abbreviation}
              </p>
              <p className="text-sm font-normal text-foreground flex items-center gap-2">
                <span className="bg-muted rounded p-1">
                  <MapPin className="h-4 w-4" />
                </span>
                {mp.constituency_name}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold font-sans">
          Search speeches
        </h2>
        <ClipsSearchBar
          searchTerm={searchTerm}
          onSearchTermChange={setSearchTerm}
          searchType={searchType}
          onSearchTypeChange={setSearchType}
          isLoading={isLoading}
        />

        <ClipsFilters
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
          total={total}
          searchTerm={searchTerm}
          displayStart={displayStart}
          displayEnd={displayEnd}
          isAISearch={searchMeta?.searchType === "hybrid"}
        />
      </div>

      {/* Clips Grid */}
      {isLoading && searchTerm ? (
        <SearchLoadingState searchType={searchType} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-0">
                <Skeleton className="aspect-video w-full rounded-t-lg" />
                <div className="p-4 space-y-3">
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : hasError ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-xl md:text-lg text-muted-foreground">
              {errorMessage || "Something went wrong loading clips."}
            </p>
            <p className="text-base md:text-sm text-muted-foreground mt-4">
              Please try again or adjust your filters.
            </p>
          </CardContent>
        </Card>
      ) : clips.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-xl md:text-lg text-muted-foreground">
              {searchTerm || dateRange.from || dateRange.to
                ? "No clips found matching your search criteria."
                : "No clips available for this MP yet."}
            </p>
            {searchTerm && (
              <p className="text-base md:text-sm text-muted-foreground mt-4">
                Try adjusting your search terms or date range.
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {clips.map((clip) => (
              <ClipCard key={clip.id} clip={clip} mp={mp} teamId={teamId} searchType={searchType} />
            ))}
          </div>

          <AllClipsPagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </div>
  );
}
