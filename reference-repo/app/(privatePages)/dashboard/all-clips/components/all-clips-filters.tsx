"use client";

import { useState } from "react";
import { Calendar, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar as CalendarComponent } from "@/components/ui/calendar";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import PartyFilter from "./party-filter";
import MPFilter from "./mp-filter";
import type { PartyOption } from "@/types/parliament";
import type { DateRange } from "react-day-picker";

interface AllClipsFiltersProps {
  parties: PartyOption[];
  selectedParties: string[];
  onPartiesChange: (parties: string[]) => void;
  selectedMemberIds: number[];
  onMemberIdsChange: (ids: number[]) => void;
  dateRange: DateRange;
  onDateRangeChange: (range: DateRange) => void;
  displayStart: number;
  displayEnd: number;
  total: number;
}

export default function AllClipsFilters({
  parties,
  selectedParties,
  onPartiesChange,
  selectedMemberIds,
  onMemberIdsChange,
  dateRange,
  onDateRangeChange,
  displayStart,
  displayEnd,
  total,
}: AllClipsFiltersProps) {
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);

  const hasDateFilter = dateRange.from || dateRange.to;
  const hasActiveFilters =
    selectedParties.length > 0 || selectedMemberIds.length > 0 || !!hasDateFilter;

  const clearAll = () => {
    onPartiesChange([]);
    onMemberIdsChange([]);
    onDateRangeChange({ from: undefined, to: undefined });
  };

  const clearDateRange = () => {
    onDateRangeChange({ from: undefined, to: undefined });
  };

  const handleDateRangeSelect = (range: DateRange | undefined) => {
    onDateRangeChange(range || { from: undefined, to: undefined });
  };

  const setQuickRange = (days: number) => {
    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - days);
    onDateRangeChange({ from, to });
    setIsCalendarOpen(false);
  };

  const setThisYear = () => {
    const now = new Date();
    const from = new Date(now.getFullYear(), 0, 1);
    const to = new Date(now.getFullYear(), 11, 31);
    onDateRangeChange({ from, to });
    setIsCalendarOpen(false);
  };

  const setLastYear = () => {
    const now = new Date();
    const from = new Date(now.getFullYear() - 1, 0, 1);
    const to = new Date(now.getFullYear() - 1, 11, 31);
    onDateRangeChange({ from, to });
    setIsCalendarOpen(false);
  };

  const getActiveQuickRange = (): number | null => {
    if (!dateRange.from || !dateRange.to) return null;

    const now = new Date();
    const diffDays = Math.round(
      (dateRange.to.getTime() - dateRange.from.getTime()) / (1000 * 60 * 60 * 24)
    );
    const toIsToday =
      Math.abs(now.getTime() - dateRange.to.getTime()) < 1000 * 60 * 60 * 24;

    if (toIsToday && diffDays >= 6 && diffDays <= 8) return 7;
    if (toIsToday && diffDays >= 29 && diffDays <= 31) return 30;

    return null;
  };

  const activeQuickRange = getActiveQuickRange();

  return (
    <div className="pt-4 pb-0">
      <div className="flex flex-col space-y-3">
        {/* Party and MP filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <PartyFilter
            parties={parties}
            selected={selectedParties}
            onChange={onPartiesChange}
          />
          <MPFilter
            selectedMemberIds={selectedMemberIds}
            onChange={onMemberIdsChange}
            selectedParties={selectedParties}
          />
        </div>

        {/* Quick filter buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setQuickRange(7)}
            className={cn(
              "min-h-[34px] min-w-[44px] px-3",
              activeQuickRange === 7 &&
                "bg-foreground text-primary-foreground border-foreground"
            )}
          >
            Last Week
          </Button>
          <Button
            variant="outline"
            onClick={() => setQuickRange(30)}
            className={cn(
              "min-h-[34px] min-w-[44px] px-3",
              activeQuickRange === 30 &&
                "bg-foreground text-primary-foreground border-foreground"
            )}
          >
            Last Month
          </Button>

          <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "justify-start text-left font-normal min-h-[34px] min-w-[44px]",
                  !dateRange.from && "text-foreground"
                )}
              >
                <Calendar className="mr-2 h-4 w-4" />
                {dateRange.from ? (
                  dateRange.to ? (
                    <>
                      {format(dateRange.from, "LLL dd, y")} -{" "}
                      {format(dateRange.to, "LLL dd, y")}
                    </>
                  ) : (
                    format(dateRange.from, "LLL dd, y")
                  )
                ) : (
                  "Date range"
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <div className="flex flex-col sm:flex-row">
                <div className="flex flex-col gap-2 p-4 sm:border-r">
                  <Button
                    variant="ghost"
                    className="justify-start min-h-[44px] px-4 py-2"
                    onClick={() => setQuickRange(7)}
                  >
                    Last 7 days
                  </Button>
                  <Button
                    variant="ghost"
                    className="justify-start min-h-[44px] px-4 py-2"
                    onClick={() => setQuickRange(30)}
                  >
                    Last 30 days
                  </Button>
                  <Button
                    variant="ghost"
                    className="justify-start min-h-[44px] px-4 py-2"
                    onClick={() => setQuickRange(90)}
                  >
                    Last 3 months
                  </Button>
                  <Button
                    variant="ghost"
                    className="justify-start min-h-[44px] px-4 py-2"
                    onClick={setThisYear}
                  >
                    This year
                  </Button>
                  <Button
                    variant="ghost"
                    className="justify-start min-h-[44px] px-4 py-2"
                    onClick={setLastYear}
                  >
                    Last year
                  </Button>
                </div>
                <div className="hidden sm:block">
                  <CalendarComponent
                    initialFocus
                    mode="range"
                    defaultMonth={dateRange.from}
                    selected={dateRange}
                    onSelect={handleDateRangeSelect}
                    numberOfMonths={2}
                  />
                </div>
                <div className="block sm:hidden">
                  <CalendarComponent
                    initialFocus
                    mode="range"
                    defaultMonth={dateRange.from}
                    selected={dateRange}
                    onSelect={handleDateRangeSelect}
                    numberOfMonths={1}
                  />
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        {/* Results Summary */}
        <div className="flex items-center gap-2">
          <p className="text-base md:text-sm text-muted-foreground">
            {total > 0
              ? `Showing ${displayStart}-${displayEnd} of ${total} clips`
              : "No clips found"}
          </p>
        </div>

        {/* Active filters */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-2">
            {hasDateFilter && (
              <Badge variant="secondary" className="gap-2 pr-1">
                Date Range
                <Button
                  variant="ghost"
                  size="sm"
                  className="min-h-[24px] min-w-[24px] h-6 w-6 p-0 hover:bg-destructive/10 hover:text-destructive rounded-sm"
                  onClick={clearDateRange}
                  aria-label="Clear date range filter"
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAll}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4 mr-1" />
              Clear filters
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
