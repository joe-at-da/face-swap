"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import ClipsSearchBar from "@/app/(privatePages)/dashboard/create-clips/components/clips-search-bar";
import SearchLoadingState from "@/app/(privatePages)/dashboard/create-clips/components/search-loading-state";
import AllClipsFilters from "./all-clips-filters";
import AllClipCard from "./all-clip-card";
import AllClipsPagination from "./all-clips-pagination";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AllClipWithMP, PartyOption } from "@/types/parliament";
import type { DateRange } from "react-day-picker";

interface AllClipsListViewProps {
  initialParties: PartyOption[];
}

const ITEMS_PER_PAGE = 24;

export default function AllClipsListView({ initialParties }: AllClipsListViewProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const isFirstFetch = useRef(true);
  const hasUrlSynced = useRef(false);

  const initialSearchTerm = searchParams.get("search") || "";
  const initialSearchType =
    searchParams.get("searchType") === "hybrid" ? "hybrid" : "text";

  const [clips, setClips] = useState<AllClipWithMP[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState(initialSearchTerm);
  const [searchType, setSearchType] = useState<"text" | "hybrid">(initialSearchType);
  const [selectedParties, setSelectedParties] = useState<string[]>([]);
  const [selectedMemberIds, setSelectedMemberIds] = useState<number[]>([]);
  const [dateRange, setDateRange] = useState<DateRange>({ from: undefined, to: undefined });

  const fetchClips = useCallback(
    async (page: number) => {
      setIsLoading(true);
      setHasError(false);
      setErrorMessage(null);
      try {
        const offset = (page - 1) * ITEMS_PER_PAGE;
        const body: Record<string, unknown> = {
          limit: ITEMS_PER_PAGE,
          offset,
          searchType,
        };

        if (searchTerm.trim()) {
          body.query = searchTerm.trim();
        }
        if (selectedParties.length > 0) {
          body.partyNames = selectedParties;
        }
        if (selectedMemberIds.length > 0) {
          body.memberIds = selectedMemberIds;
        }
        if (dateRange.from) {
          body.dateFrom = dateRange.from.toISOString().split("T")[0];
        }
        if (dateRange.to) {
          body.dateTo = dateRange.to.toISOString().split("T")[0];
        }

        const res = await fetch("/api/clips/search-all", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (res.ok) {
          const data = await res.json();
          setClips(data.clips || []);
          setTotal(data.total || 0);
        } else {
          const errorData = await res.json().catch(() => ({}));
          setErrorMessage(errorData.error || "Something went wrong loading clips.");
          setClips([]);
          setTotal(0);
          setHasError(true);
        }
      } catch {
        setErrorMessage("Something went wrong loading clips.");
        setClips([]);
        setTotal(0);
        setHasError(true);
      } finally {
        setIsLoading(false);
      }
    },
    [searchTerm, searchType, selectedParties, selectedMemberIds, dateRange]
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

  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
  const displayStart = total > 0 ? (currentPage - 1) * ITEMS_PER_PAGE + 1 : 0;
  const displayEnd = Math.min(currentPage * ITEMS_PER_PAGE, total);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-foreground pt-4">All Parliament Clips</h1>

      <ClipsSearchBar
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        searchType={searchType}
        onSearchTypeChange={setSearchType}
        isLoading={isLoading}
      />

      <AllClipsFilters
        parties={initialParties}
        selectedParties={selectedParties}
        onPartiesChange={setSelectedParties}
        selectedMemberIds={selectedMemberIds}
        onMemberIdsChange={setSelectedMemberIds}
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        displayStart={displayStart}
        displayEnd={displayEnd}
        total={total}
      />

      {isLoading && searchTerm ? (
        <SearchLoadingState searchType={searchType} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-0">
                <Skeleton className="aspect-video w-full rounded-t-lg" />
                <div className="p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-6 w-6 rounded-full" />
                    <Skeleton className="h-4 w-24" />
                  </div>
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
            <p className="text-lg text-muted-foreground">
              {errorMessage || "Something went wrong loading clips."}
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Please try again or adjust your filters.
            </p>
          </CardContent>
        </Card>
      ) : clips.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-lg text-muted-foreground">
              {searchTerm || selectedParties.length > 0 || selectedMemberIds.length > 0 || dateRange.from
                ? "No clips found matching your criteria."
                : "No clips available."}
            </p>
            {searchTerm && (
              <p className="text-sm text-muted-foreground mt-2">
                Try adjusting your search or filters.
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {clips.map((clip) => (
              <AllClipCard key={clip.id} clip={clip} />
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
