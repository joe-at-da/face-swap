"use client";

import { useState, useMemo } from "react";
import { Calendar, Play } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface SummaryCard {
  date: string;
  title: string;
  description: string;
  topics: string[];
  videoCount: number;
}

export default function PrimeMinistersQuestionsPage() {
  const ITEMS_PER_PAGE = 12;
  const [currentPage, setCurrentPage] = useState(1);
  const [sortOrder, setSortOrder] = useState("newest");

  // Parse date string to Date object for sorting
  const parseDate = (dateString: string): Date => {
    // Format: "19 November 2025" or "28 October 2025"
    return new Date(dateString);
  };

  // Sample data - in a real app, this would come from an API
  const allSummariesRaw: SummaryCard[] = useMemo(
    () => [
      {
        date: "19 November 2025",
        title: "PMQs 19 November 2025",
        description:
          "PMQs this week centered on climate commitments ahead of international negotiations. Ed Davey questioned the Prime Minister's commitment to meeting...",
        topics: [
          "Healthcare Reform",
          "NHS Funding",
          "Mental Health",
          "Education",
          "Local Government",
        ],
        videoCount: 3,
      },
      {
        date: "12 November 2025",
        title: "PMQs 12 November 2025",
        description:
          "This week's session focused on economic policy and inflation concerns, with questions about the cost of living crisis and support for families...",
        topics: ["Economic Policy", "Cost of Living", "Housing"],
        videoCount: 2,
      },
      {
        date: "5 November 2025",
        title: "PMQs 5 November 2025",
        description:
          "Discussions centered on immigration policy and border security, with questions about the government's approach to managing migration...",
        topics: ["Immigration", "Border Security", "Foreign Policy"],
        videoCount: 4,
      },
      // Add more cards to demonstrate pagination
      ...Array.from({ length: 15 }, (_, i) => ({
        date: `${28 - i} October 2025`,
        title: `PMQs ${28 - i} October 2025`,
        description: `Weekly Prime Minister's Questions session covering various topics including policy discussions and parliamentary debates...`,
        topics: ["Policy", "Debate", "Parliament"],
        videoCount: (i % 5) + 1, // Deterministic value based on index
      })),
    ],
    []
  );

  // Sort summaries based on sortOrder
  const allSummaries = useMemo(() => {
    const sorted = [...allSummariesRaw].sort((a, b) => {
      const dateA = parseDate(a.date);
      const dateB = parseDate(b.date);

      if (sortOrder === "newest") {
        // Newest first: descending order (newer dates first)
        return dateB.getTime() - dateA.getTime();
      } else {
        // Oldest first: ascending order (older dates first)
        return dateA.getTime() - dateB.getTime();
      }
    });
    return sorted;
  }, [sortOrder, allSummariesRaw]);

  const totalPages = Math.ceil(allSummaries.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedSummaries = allSummaries.slice(startIndex, endIndex);

  const renderCard = (summary: SummaryCard, index: number) => (
    <Card
      key={index}
      className="rounded border bg-card p-6 h-full flex flex-col"
    >
      <CardContent className="p-0 space-y-4 flex-1 flex flex-col">
        <div className="flex items-center gap-2 text-muted-foreground text-sm font-sans">
          <Calendar className="h-4 w-4" />
          <span>{summary.date}</span>
        </div>
        <h4 className="text-foreground font-bold text-base font-sans">
          {summary.title}
        </h4>
        <p className="text-foreground font-normal text-sm font-sans">
          {summary.description}
        </p>
        <div className="flex flex-wrap gap-2">
          {summary.topics.map((topic, topicIndex) => (
            <Badge
              key={topicIndex}
              className="text-xs font-sans bg-slate-200 text-primary rounded"
            >
              {topic}
            </Badge>
          ))}
        </div>
        <div className="flex items-center gap-2 text-muted-foreground text-sm font-sans mt-auto">
          <Play className="h-4 w-4" />
          <span>
            {summary.videoCount} video{summary.videoCount !== 1 ? "s" : ""}
          </span>
        </div>
      </CardContent>
    </Card>
  );
  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h1
          className="text-2xl font-bold text-foreground tracking-tight pt-4"
          style={{ fontFamily: "var(--font-family-sans, Inter)" }}
        >
          Prime Minister&apos;s Questions
        </h1>
        <p className="text-base text-muted-foreground font-normal leading-relaxed">
          Weekly summaries of Prime Minister&apos;s Questions - politically
          neutral analysis with party-specific breakdowns
        </p>
      </div>

      <div className="rounded border bg-card p-6">
        <div className="flex items-center justify-between pb-4 flex-wrap gap-2">
          <h2 className="text-foreground font-bold text-lg font-sans">
            Prime Minister&apos;s Questions - 26 November 2025
          </h2>
          <div className="flex items-center gap-2 text-muted-foreground text-sm font-sans">
            <Calendar className="h-4 w-4" />
            <span>Week 47 (18-24 November 2024)</span>
          </div>
        </div>
        <span className="text-muted-foreground font-normal text-sm font-sans py-4">
          Overview
        </span>
        <p className="text-foreground font-normal text-base py-4">
          Content for Prime Minister&apos;s Questions will appear here. Prime
          Minister&apos;s Questions on 20 November 2025 was dominated by
          discussions on NHS waiting lists and healthcare funding, with the
          Leader of the Opposition mounting a sustained challenge on the
          government&apos;s record. The session also featured questions on
          housing policy, small business support, and educational standards. The
          exchanges were robust but focused primarily on domestic policy areas,
          with the Prime Minister defending the government&apos;s economic
          record whilst facing pressure on public service delivery.
        </p>
        <span className="text-muted-foreground font-normal text-sm font-sans py-8">
          Main topics
        </span>
        <div className="flex flex-wrap gap-2 pt-2">
          <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
            NHS waiting lists
          </Badge>
          <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
            Healthcare funding
          </Badge>
          <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
            Housing policy
          </Badge>
          <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
            Small business support
          </Badge>
          <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
            Educational standards
          </Badge>
        </div>
      </div>

      <div className="flex items-center justify-between pt-4">
        <h3 className="text-foreground font-bold text-lg font-sans">
          Previous Summaries
        </h3>
        <Select
          value={sortOrder}
          onValueChange={(value) => {
            setSortOrder(value);
            setCurrentPage(1); // Reset to first page when sorting changes
          }}
        >
          <SelectTrigger className="w-[140px] bg-slate-100 text-primary font-sans text-sm border-0 [&_svg]:!text-primary [&_svg]:!opacity-100">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">Newest first</SelectItem>
            <SelectItem value="oldest">Oldest first</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {paginatedSummaries.map((summary, index) =>
          renderCard(summary, startIndex + index)
        )}
      </div>

      {/* Pagination Controls */}
      {allSummaries.length > ITEMS_PER_PAGE && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  if (currentPage > 1) {
                    setCurrentPage(currentPage - 1);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }
                }}
                className={`[&>span]:hidden ${
                  currentPage === 1 ? "pointer-events-none opacity-50" : ""
                }`}
              />
            </PaginationItem>

            {/* Page Numbers */}
            {(() => {
              const pages: (number | "ellipsis")[] = [];
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
                  pages.push("ellipsis");
                  pages.push(totalPages);
                } else if (currentPage >= totalPages - 3) {
                  // Near the end: 1 ... (n-4) (n-3) (n-2) (n-1) n
                  pages.push("ellipsis");
                  for (let i = totalPages - 4; i <= totalPages; i++) {
                    pages.push(i);
                  }
                } else {
                  // In the middle: 1 ... (current-1) current (current+1) ... last
                  pages.push("ellipsis");
                  for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                    pages.push(i);
                  }
                  pages.push("ellipsis");
                  pages.push(totalPages);
                }
              }

              return pages.map((item, index) => {
                if (item === "ellipsis") {
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
                        window.scrollTo({ top: 0, behavior: "smooth" });
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
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }
                }}
                className={`[&>span]:hidden ${
                  currentPage === totalPages
                    ? "pointer-events-none opacity-50"
                    : ""
                }`}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  );
}
