"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Search,
  ChevronDown,
  ChevronUp,
  Check,
  Loader2,
  Video,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

interface MP {
  member_id: number;
  display_name: string;
  party_abbreviation: string;
  party_name: string | null;
  constituency_name: string | null;
  parliament_member_portraits: Array<{
    image_url: string;
    is_primary: boolean | null;
  }>;
}

interface MpSearchPanelProps {
  selectedMemberId: number | null;
  onSelect: (memberId: number) => void;
  defaultOpen?: boolean;
  sessionDate: string | null;
}

const PARTY_COLORS: Record<string, string> = {
  Lab: "bg-red-500",
  Con: "bg-blue-500",
  SNP: "bg-yellow-500",
  LD: "bg-orange-500",
  Green: "bg-green-500",
  DUP: "bg-red-700",
  SF: "bg-green-700",
  PC: "bg-green-600",
  SDLP: "bg-green-500",
  Alliance: "bg-yellow-600",
};

export function MpSearchPanel({
  selectedMemberId,
  onSelect,
  defaultOpen = false,
  sessionDate,
}: MpSearchPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<MP[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Debounced search
  const performSearch = useCallback(async (term: string) => {
    if (!term || term.length < 2) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);

    try {
      const response = await fetch(
        `/api/setup/mps?search=${encodeURIComponent(term)}`
      );

      if (!response.ok) {
        throw new Error("Failed to search MPs");
      }

      const data = await response.json();
      setSearchResults(data.mps || []);
    } catch (error) {
      console.error("Error searching MPs:", error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(searchTerm);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm, performSearch]);

  const handleGoogleImageSearch = (e: React.MouseEvent, mp: MP) => {
    e.stopPropagation(); // Prevent MP selection when clicking search button
    const searchQuery = `${mp.display_name} uk mp`;
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(
      searchQuery
    )}&tbm=isch`;
    window.open(searchUrl, "_blank");
  };

  const handleParliamentLiveSearch = (e: React.MouseEvent, mp: MP) => {
    e.stopPropagation(); // Prevent MP selection when clicking search button

    // Format session date as DD/MM/YYYY (UK format) if available
    let startDate = "";
    let endDate = "";
    if (sessionDate) {
      try {
        // Parse ISO date string (YYYY-MM-DD) directly to avoid timezone issues
        const dateMatch = sessionDate.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (dateMatch) {
          const [, year, month, day] = dateMatch;
          const formattedDate = `${day}/${month}/${year}`;
          startDate = formattedDate;
          endDate = formattedDate;
        } else {
          // Fallback to Date parsing if format is different
          const date = new Date(sessionDate);
          if (!isNaN(date.getTime())) {
            const day = String(date.getDate()).padStart(2, "0");
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const year = date.getFullYear();
            const formattedDate = `${day}/${month}/${year}`;
            startDate = formattedDate;
            endDate = formattedDate;
          }
        }
      } catch (error) {
        console.error("Error formatting date:", error);
      }
    }

    // Build the ParliamentLive.tv search URL
    const memberName = `${mp.display_name} MP`;
    const params = new URLSearchParams({
      Keywords: "",
      Member: memberName,
      MemberId: mp.member_id.toString(),
      House: "",
      Business: "",
      ...(startDate && { Start: startDate }),
      ...(endDate && { End: endDate }),
    });

    const searchUrl = `https://www.parliamentlive.tv/Search?${params.toString()}`;
    window.open(searchUrl, "_blank");
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-lg border border-border">
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between p-4 hover:bg-muted/50"
          >
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4" />
              <span className="font-medium">Search for a different MP</span>
            </div>
            {isOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </CollapsibleTrigger>

        <CollapsibleContent className="border-t border-border">
          <div className="space-y-4 p-4">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name, party, constituency, or member ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
              )}
            </div>

            {/* Search Results */}
            {searchTerm.length >= 2 && (
              <div className="space-y-2">
                {searchResults.length === 0 && !isSearching && (
                  <p className="py-8 text-center text-sm text-muted-foreground">
                    No MPs found matching &quot;{searchTerm}&quot;
                  </p>
                )}

                {searchResults.length > 0 && (
                  <div className="grid max-h-[600px] grid-cols-2 gap-4 overflow-y-auto">
                    {searchResults.map((mp) => {
                      const isSelected = selectedMemberId === mp.member_id;
                      const partyColor =
                        PARTY_COLORS[mp.party_abbreviation] || "bg-gray-500";
                      const primaryPortrait =
                        mp.parliament_member_portraits.find(
                          (p) => p.is_primary
                        );
                      const portraitUrl =
                        primaryPortrait?.image_url ||
                        mp.parliament_member_portraits[0]?.image_url;

                      return (
                        <Button
                          key={mp.member_id}
                          type="button"
                          variant="outline"
                          onClick={() => {
                            onSelect(mp.member_id);
                            setIsOpen(false);
                          }}
                          className={cn(
                            "h-auto w-full flex-col gap-3 p-4 text-left transition-all hover:scale-[1.02]",
                            isSelected &&
                              "border-primary bg-primary/5 shadow-md"
                          )}
                        >
                          {/* Portrait */}
                          <div className="relative h-64 w-full overflow-hidden rounded-lg bg-muted">
                            {portraitUrl ? (
                              <img
                                src={portraitUrl}
                                alt={mp.display_name}
                                className="absolute inset-0 h-full w-full object-cover"
                                loading="lazy"
                              />
                            ) : (
                              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                                No Image
                              </div>
                            )}

                            {/* Selection Indicator */}
                            {isSelected && (
                              <div className="absolute inset-0 flex items-center justify-center bg-primary/30">
                                <div className="rounded-full bg-primary p-3">
                                  <Check className="h-6 w-6 text-primary-foreground" />
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Info */}
                          <div className="w-full space-y-2">
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-lg font-semibold leading-tight">
                                {mp.display_name}
                              </p>
                              <div className="flex items-center gap-1">
                                {/* Google Image Search Button */}
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  onClick={(e) =>
                                    handleGoogleImageSearch(e, mp)
                                  }
                                  className="h-7 w-7 flex-shrink-0"
                                  title="Search Google Images"
                                >
                                  <Search className="h-4 w-4" />
                                </Button>
                                {/* ParliamentLive.tv Search Button */}
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  onClick={(e) =>
                                    handleParliamentLiveSearch(e, mp)
                                  }
                                  className="h-7 w-7 flex-shrink-0"
                                  title="Search ParliamentLive.tv"
                                >
                                  <Video className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              <Badge
                                className={cn(partyColor, "text-sm text-white")}
                              >
                                {mp.party_abbreviation}
                              </Badge>
                              {mp.constituency_name && (
                                <Badge variant="outline" className="text-sm">
                                  {mp.constituency_name}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </Button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {searchTerm.length < 2 && (
              <p className="py-4 text-center text-sm text-muted-foreground">
                Type at least 2 characters to search
              </p>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}
