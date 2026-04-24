"use client";

import { useState } from "react";
import { Calendar, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar as CalendarComponent } from "@/components/ui/calendar";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import type { DateRange } from "react-day-picker";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface MyClipsFiltersProps {
  dateRange: DateRange;
  onDateRangeChange: (range: DateRange) => void;
  status: string;
  onStatusChange: (status: string) => void;
}

const statusOptions = [
  { value: "all", label: "All Statuses" },
  { value: "pending_review", label: "Pending Review" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

export default function MyClipsFilters({
  dateRange,
  onDateRangeChange,
  status,
  onStatusChange
}: MyClipsFiltersProps) {
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);

  const handleDateRangeSelect = (range: DateRange | undefined) => {
    onDateRangeChange(range || { from: undefined, to: undefined });
  };

  const clearDateRange = () => {
    onDateRangeChange({ from: undefined, to: undefined });
  };

  const clearStatus = () => {
    onStatusChange("all");
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

  const hasActiveFilters = (dateRange.from || dateRange.to) || status !== "all";

  return (
    <div>
      <div className="flex flex-col space-y-4">
        <div className="flex flex-wrap items-center gap-4 mt-4">
          {/* Status Filter */}
          <Select value={status} onValueChange={onStatusChange}>
            <SelectTrigger className="min-h-[34px] min-w-[120px] cursor-pointer [&_svg]:!text-foreground [&_svg]:!opacity-100">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              {statusOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Quick filter buttons */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => setQuickRange(7)}
              className="min-h-[34px] min-w-[44px] px-3"
            >
              Last Week
            </Button>
            <Button
              variant="default"
              onClick={() => setQuickRange(30)}
              className="min-h-[34px] min-w-[44px] px-3"
            >
              Last Month
            </Button>
          </div>

          {/* Date Range Filter */}
          <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "justify-start text-left font-normal min-h-[34px] min-w-[44px] text-foreground",
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

        {/* Active filters */}
        <div className="flex flex-wrap items-center gap-2">
          {(dateRange.from || dateRange.to) && (
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
          {status !== "all" && (
            <Badge variant="secondary" className="gap-2 pr-1">
              Status: {statusOptions.find(opt => opt.value === status)?.label}
              <Button
                variant="ghost"
                size="sm"
                className="min-h-[24px] min-w-[24px] h-6 w-6 p-0 hover:bg-destructive/10 hover:text-destructive rounded-sm"
                onClick={clearStatus}
                aria-label="Clear status filter"
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          )}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                clearDateRange();
                clearStatus();
              }}
              className="text-xs"
            >
              Clear All
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}