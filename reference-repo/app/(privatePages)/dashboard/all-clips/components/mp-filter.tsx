"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { SmartAvatar } from "@/components/smart-avatar";
import type { MPOption } from "@/types/parliament";

interface MPFilterProps {
  selectedMemberIds: number[];
  onChange: (ids: number[]) => void;
  selectedParties: string[];
  /** Override the API endpoint used to fetch MP options (default: /api/clips/filter-options) */
  apiEndpoint?: string;
  /** Extra query params to forward with every request (e.g. teamId) */
  extraParams?: Record<string, string>;
}

export default function MPFilter({ selectedMemberIds, onChange, selectedParties, apiEndpoint, extraParams }: MPFilterProps) {
  const [open, setOpen] = useState(false);
  const [mps, setMps] = useState<MPOption[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  // Cache MP data for badge display (survives dropdown close / re-fetch)
  const mpCacheRef = useRef<Map<number, MPOption>>(new Map());

  const fetchMPs = useCallback(async (searchTerm: string) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ type: "mps" });
      if (selectedParties.length > 0) {
        params.set("party", selectedParties.join(","));
      }
      if (searchTerm) {
        params.set("search", searchTerm);
      }
      if (extraParams) {
        for (const [key, value] of Object.entries(extraParams)) {
          params.set(key, value);
        }
      }
      const endpoint = apiEndpoint || "/api/clips/filter-options";
      const res = await fetch(`${endpoint}?${params}`);
      if (res.ok) {
        const data = await res.json();
        const fetchedMps = (data.mps || []) as MPOption[];
        setMps(fetchedMps);
        // Update cache with fetched data
        for (const mp of fetchedMps) {
          mpCacheRef.current.set(mp.member_id, mp);
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [selectedParties, apiEndpoint, extraParams]);

  // Fetch on open or when fetchMPs identity changes (covers selectedParties, apiEndpoint, extraParams)
  // search intentionally omitted – search-triggered fetches go through handleSearchChange debounce
  useEffect(() => {
    if (open) {
      fetchMPs(search);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, fetchMPs]);

  // Debounced search - sole path for search-triggered fetches
  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchMPs(value);
    }, 300);
  };

  const toggleMP = (mp: MPOption) => {
    if (selectedMemberIds.includes(mp.member_id)) {
      onChange(selectedMemberIds.filter((id) => id !== mp.member_id));
    } else {
      mpCacheRef.current.set(mp.member_id, mp);
      onChange([...selectedMemberIds, mp.member_id]);
    }
  };

  const removeMP = (memberId: number) => {
    onChange(selectedMemberIds.filter((id) => id !== memberId));
  };

  // Derive badge display from cache + selectedMemberIds (no separate state needed)
  const displayMPs = selectedMemberIds
    .map((id) => mpCacheRef.current.get(id))
    .filter((mp): mp is MPOption => mp !== undefined);

  return (
    <div className="flex flex-col gap-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full sm:w-[200px] justify-between"
          >
            {selectedMemberIds.length > 0
              ? `${selectedMemberIds.length} ${selectedMemberIds.length === 1 ? "MP" : "MPs"}`
              : "Filter by MP"}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[320px] p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search MPs..."
              value={search}
              onValueChange={handleSearchChange}
            />
            <CommandList>
              {isLoading ? (
                <div className="py-6 text-center text-sm text-muted-foreground">
                  Loading...
                </div>
              ) : mps.length === 0 ? (
                <CommandEmpty>No MPs found.</CommandEmpty>
              ) : (
                <CommandGroup>
                  {mps.map((mp) => (
                    <CommandItem
                      key={mp.member_id}
                      value={String(mp.member_id)}
                      onSelect={() => toggleMP(mp)}
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <SmartAvatar
                          profileImage={mp.portrait_url}
                          firstName={mp.display_name?.split(" ")[0]}
                          lastName={mp.display_name?.split(" ").slice(1).join(" ")}
                          className="h-8 w-8 shrink-0"
                        />
                        <span className="truncate text-sm">{mp.display_name}</span>
                        {mp.party_abbreviation && (
                          <Badge
                            variant="outline"
                            className="ml-auto shrink-0 text-[10px] px-1.5 py-0"
                            style={{
                              backgroundColor: mp.party_background_colour
                                ? `#${mp.party_background_colour}20`
                                : undefined,
                              borderColor: mp.party_background_colour
                                ? `#${mp.party_background_colour}`
                                : undefined,
                            }}
                          >
                            {mp.party_abbreviation}
                          </Badge>
                        )}
                      </div>
                      {selectedMemberIds.includes(mp.member_id) && (
                        <Check className="h-4 w-4 shrink-0" />
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {displayMPs.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {displayMPs.map((mp) => (
            <Badge key={mp.member_id} variant="secondary" className="gap-1 pr-1">
              <SmartAvatar
                profileImage={mp.portrait_url}
                firstName={mp.display_name?.split(" ")[0]}
                lastName={mp.display_name?.split(" ").slice(1).join(" ")}
                className="h-4 w-4"
              />
              <span className="text-xs truncate max-w-[100px]">{mp.display_name}</span>
              <button
                type="button"
                onClick={() => removeMP(mp.member_id)}
                className="ml-0.5 rounded-sm hover:bg-muted p-0.5"
                aria-label={`Remove ${mp.display_name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-xs text-muted-foreground hover:text-foreground underline"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
