"use client";

import { Badge } from "@/components/ui/badge";
import { Sparkles } from "lucide-react";

interface SearchTermsDisplayProps {
  searchTerms: string[];
}

export default function SearchTermsDisplay({
  searchTerms,
}: SearchTermsDisplayProps) {
  if (searchTerms.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-muted-foreground flex items-center gap-1">
        <Sparkles className="h-3 w-3" />
        AI searched for:
      </span>
      {searchTerms.map((term) => (
        <Badge key={term} variant="outline" className="text-xs font-normal">
          {term}
        </Badge>
      ))}
    </div>
  );
}
