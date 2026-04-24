"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Loader2, Sparkles, Type, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface ClipsSearchBarProps {
  searchTerm: string;
  onSearchTermChange: (term: string) => void;
  searchType: "text" | "hybrid";
  onSearchTypeChange: (type: "text" | "hybrid") => void;
  isLoading: boolean;
}

export default function ClipsSearchBar({
  searchTerm,
  onSearchTermChange,
  searchType,
  onSearchTypeChange,
  isLoading,
}: ClipsSearchBarProps) {
  // Local state for the input value to prevent losing text while typing
  const [localValue, setLocalValue] = useState(searchTerm);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isTypingRef = useRef(false);
  const lastTypedValueRef = useRef(searchTerm);

  // Sync local value when searchTerm changes externally (e.g., from URL params)
  // But only if we're not currently typing
  useEffect(() => {
    if (!isTypingRef.current && searchTerm !== lastTypedValueRef.current) {
      setLocalValue(searchTerm);
      lastTypedValueRef.current = searchTerm;
    }
  }, [searchTerm]);

  // Debounced handler that updates the parent state
  const handleInputChange = (value: string) => {
    // Update local value immediately for responsive typing
    setLocalValue(value);
    lastTypedValueRef.current = value;
    isTypingRef.current = true;

    // Clear existing timeout
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    // Debounce the parent state update
    debounceTimeoutRef.current = setTimeout(() => {
      isTypingRef.current = false;
      onSearchTermChange(value);
    }, 1000); // Debounce time set to 1000ms
  };

  const handleClear = () => {
    setLocalValue("");
    lastTypedValueRef.current = "";
    isTypingRef.current = false;
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
      debounceTimeoutRef.current = null;
    }
    onSearchTermChange("");
  };

  // Handle Enter key to trigger search immediately
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      // Clear any pending debounce
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
        debounceTimeoutRef.current = null;
      }

      // Trigger search immediately
      isTypingRef.current = false;
      onSearchTermChange(localValue);
    }
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  const placeholder =
    searchType === "hybrid"
      ? "Search by context or topic - use 2+ words for best results"
      : "Search for exact words or phrases...";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Button
          variant={searchType === "text" ? "default" : "outline"}
          size="sm"
          onClick={() => onSearchTypeChange("text")}
          className="h-8"
        >
          <Type className="h-3.5 w-3.5 mr-1.5" />
          Text Search
        </Button>
        <Button
          variant={searchType === "hybrid" ? "default" : "outline"}
          size="sm"
          onClick={() => onSearchTypeChange("hybrid")}
          className="h-8"
        >
          <Sparkles className="h-3.5 w-3.5 mr-1.5" />
          AI Search
        </Button>
      </div>
      <div className="relative max-w-2xl">
        <Input
          placeholder={placeholder}
          value={localValue}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          className="pr-16 min-h-[34px] text-base w-full bg-muted rounded-sm"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {localValue && !isLoading && (
            <button
              type="button"
              onClick={handleClear}
              className="p-0.5 rounded-sm hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            <Search className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>
    </div>
  );
}
