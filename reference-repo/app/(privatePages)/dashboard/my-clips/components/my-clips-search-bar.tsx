"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";

interface MyClipsSearchBarProps {
  searchTerm: string;
  onSearchTermChange: (term: string) => void;
  isLoading: boolean;
}

export default function MyClipsSearchBar({
  searchTerm,
  onSearchTermChange,
  isLoading,
}: MyClipsSearchBarProps) {
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

  return (
    <div>
      <div className="space-y-4">
        <div className="relative max-w-2xl">
          <Input
            placeholder="Search clips by transcript content or topic..."
            value={localValue}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pr-10 min-h-[34px] text-base w-full bg-slate-100 rounded-sm"
          />
          {isLoading ? (
            <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
          ) : (
            <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          )}
        </div>
      </div>
    </div>
  );
}
