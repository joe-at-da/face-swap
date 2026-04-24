"use client";

import { useState, useMemo } from "react";
import { Calendar as CalendarIcon, UserCircle, MonitorPlay, Clock, Play, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import PreviewVideo from "@/app/(privatePages)/dashboard/create-clips/components/preview-video";
import { formatDuration } from "@/lib/formatDuration";
import {
    Pagination,
    PaginationContent,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
    PaginationEllipsis,
} from "@/components/ui/pagination";

interface SummaryCard {
    date: string;
    description: string;
    parliamentaryMember: string;
    createdDate: string;
    clip_url?: string | null;
    thumbnail_url?: string | null;
    duration_seconds?: number | null;
}

export default function LiberalDemocratsPage() {
    const ITEMS_PER_PAGE = 12;
    const [currentPage, setCurrentPage] = useState(1);
    const [viewMode, setViewMode] = useState<"weekly" | "monthly">("weekly");
    const [selectedDate, setSelectedDate] = useState<Date>(new Date(2024, 10, 18)); // November 18, 2024
    const [isCalendarOpen, setIsCalendarOpen] = useState(false);
    const [actualDurations, setActualDurations] = useState<Record<number, number | null>>({});

    // Format date to "3 Nov, 2025" format
    const formatCreatedDate = (dateString: string): string => {
        const date = new Date(dateString);
        const day = date.getDate();
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = monthNames[date.getMonth()];
        const year = date.getFullYear();
        return `${day} ${month}, ${year}`;
    };

    const handleDurationLoaded = (index: number, duration: number) => {
        setActualDurations(prev => ({ ...prev, [index]: duration }));
    };

    // Get week number and date range for a given date
    const getWeekInfo = (date: Date) => {
        // Create a copy to avoid mutating the original date
        const dateCopy = new Date(date);

        // Get start of year
        const startOfYear = new Date(dateCopy.getFullYear(), 0, 1);

        // Calculate week number (ISO week)
        const pastDaysOfYear = (dateCopy.getTime() - startOfYear.getTime()) / 86400000;
        const weekNumber = Math.ceil((pastDaysOfYear + startOfYear.getDay() + 1) / 7);

        // Get start of week (Monday)
        const day = dateCopy.getDay();
        const diff = dateCopy.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
        const startOfWeek = new Date(dateCopy);
        startOfWeek.setDate(diff);

        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(startOfWeek.getDate() + 6);

        const monthNames = ["January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"];
        const startDay = startOfWeek.getDate();
        const endDay = endOfWeek.getDate();
        const endMonth = monthNames[endOfWeek.getMonth()];
        const year = startOfWeek.getFullYear();

        // Format: "18-24 November 2024"
        const range = startOfWeek.getMonth() === endOfWeek.getMonth()
            ? `${startDay}-${endDay} ${endMonth} ${year}`
            : `${startDay} ${monthNames[startOfWeek.getMonth()]} - ${endDay} ${endMonth} ${year}`;

        return {
            weekNumber,
            range
        };
    };

    const weekInfo = useMemo(() => getWeekInfo(selectedDate), [selectedDate]);

    // Sample data - in a real app, this would come from an API
    const allSummaries: SummaryCard[] = useMemo(() => [
        {
            date: "19 November 2025",
            description: "Liberal Democrat MPs this week focused on environmental policy and climate action, with Ed Davey leading calls for stronger commitments ahead of international negotiations...",
            parliamentaryMember: "Ed Davey",
            createdDate: "20 November 2025",
        },
        {
            date: "12 November 2025",
            description: "This week's Liberal Democrat contributions centered on social care reform and mental health services, with emphasis on community-based support and early intervention...",
            parliamentaryMember: "Sarah Green",
            createdDate: "13 November 2025",
        },
        {
            date: "5 November 2025",
            description: "Liberal Democrat MPs raised concerns about housing affordability and rental market reforms, advocating for stronger tenant protections and affordable housing initiatives...",
            parliamentaryMember: "Daisy Cooper",
            createdDate: "6 November 2025",
        },
        // Add more cards to demonstrate pagination
        ...Array.from({ length: 15 }, (_, i) => ({
            date: `${28 - i} October 2025`,
            description: `Weekly Liberal Democrat parliamentary activity covering various policy areas including education, healthcare, and democratic reform...`,
            parliamentaryMember: `MP ${i + 1}`,
            createdDate: `${29 - i} October 2025`,
        })),
    ], []);

    const totalPages = Math.ceil(allSummaries.length / ITEMS_PER_PAGE);
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const paginatedSummaries = allSummaries.slice(startIndex, endIndex);

    const renderCard = (summary: SummaryCard, index: number) => (
        <Card key={index} className="rounded border bg-card h-full flex flex-col overflow-hidden py-0">
            <CardContent className="p-0 flex-1 flex flex-col">
                {/* Video Preview */}
                <div className="relative aspect-video bg-muted overflow-hidden">
                    {summary.thumbnail_url || summary.clip_url ? (
                        <PreviewVideo
                            src={summary.clip_url || null}
                            poster={summary.thumbnail_url || null}
                            onDurationLoaded={(duration) => handleDurationLoaded(index, duration)}
                        />
                    ) : (
                        <div className="w-full h-full bg-slate-200 flex items-center justify-center">
                            <span className="text-muted-foreground text-sm font-sans">No thumbnail</span>
                        </div>
                    )}

                    {/* Play button overlay */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="bg-white/90 hover:bg-white rounded-full min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors shadow-lg">
                            <Play className="h-6 w-6 text-foreground fill-foreground" />
                        </div>
                    </div>

                    {/* Duration badge */}
                    <div className="absolute bottom-2 right-2 bg-white text-foreground px-2 py-1 rounded text-sm md:text-xs font-medium z-10">
                        <Clock className="h-3 w-3 inline mr-1" />
                        {formatDuration(actualDurations[index] ?? summary.duration_seconds ?? null)}
                    </div>
                </div>

                <div className="p-6 space-y-4 flex-1 flex flex-col">
                    <div className="flex">
                        <span className="text-muted-foreground font-normal text-sm font-sans">
                            Parliamentary session
                        </span>
                        <div className="flex items-center gap-1.5 text-primary text-sm font-sans ml-auto">
                            <CalendarIcon className="h-4 w-4 md:h-3 md:w-3 text-muted-foreground" />
                            <span className="font-sans text-muted-foreground">{summary.date}</span>
                        </div>
                    </div>
                    <p className="text-foreground font-normal text-sm font-sans">
                        {summary.description}
                    </p>
                    <div className="space-y-1.5">
                        <div className="flex items-center gap-0.5 text-primary text-xs font-sans">
                            <div className="flex items-center justify-center  rounded bg-slate-200 p-1">
                                <UserCircle className="h-2.5 w-2.5 text-primary" />
                            </div>
                            <span>{summary.parliamentaryMember}</span>
                        </div>
                        <div className="flex items-center gap-0.5 text-primary text-xs font-sans ">
                            <div className="flex items-center justify-center  rounded bg-slate-200 p-1">
                                <MonitorPlay className="h-2.5 w-2.5  text-primary" />
                            </div>
                            <span>Created {formatCreatedDate(summary.createdDate)}</span>
                        </div>
                    </div>
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
                    Party Activity Summary
                </h1>
                <p className="text-base text-muted-foreground font-normal leading-relaxed pb-4">
                    Overview of Liberal Democrat parliamentary activity
                </p>
                <div className="flex items-center justify-between gap-4">
                    <ToggleGroup
                        type="single"
                        value={viewMode}
                        onValueChange={(value) => {
                            if (value === "weekly" || value === "monthly") {
                                setViewMode(value);
                            }
                        }}
                        variant="outline"
                        className="w-fit"
                    >
                        <ToggleGroupItem value="weekly" aria-label="Weekly view">
                            Weekly
                        </ToggleGroupItem>
                        <ToggleGroupItem value="monthly" aria-label="Monthly view">
                            Monthly
                        </ToggleGroupItem>
                    </ToggleGroup>
                    <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
                        <PopoverTrigger asChild>
                            <Button
                                variant="outline"
                                className="w-fit bg-slate-100 text-primary font-sans text-sm border-0 [&_svg]:!text-primary [&_svg]:!opacity-100 justify-start text-left font-normal"
                            >
                                <CalendarIcon className="mr-2 h-4 w-4" />
                                Week {weekInfo.weekNumber} ({weekInfo.range})
                                <ChevronDown className="ml-2 h-4 w-4" />
                            </Button>
                        </PopoverTrigger>
                        {isCalendarOpen && (
                            <PopoverContent className="w-auto p-0" align="end">
                                <Calendar
                                    mode="single"
                                    selected={selectedDate}
                                    onSelect={(date) => {
                                        if (date) {
                                            setSelectedDate(date);
                                            setIsCalendarOpen(false);
                                        }
                                    }}
                                    initialFocus
                                />
                            </PopoverContent>
                        )}
                    </Popover>
                </div>
            </div>

            <div className="rounded border bg-card p-6">
                <div className="flex items-center justify-between pb-4 flex-wrap gap-2">
                    <h2 className="text-foreground font-bold text-lg font-sans">
                        Weekly Summary for Week 47
                    </h2>
                    <div className="flex items-center gap-2 text-muted-foreground text-sm font-sans">
                        <CalendarIcon className="h-4 w-4" />
                        <span>Week 47 (18-24 November 2024)</span>
                    </div>
                </div>
                <span className="text-muted-foreground font-normal text-sm font-sans py-4">
                    Overview
                </span>
                <p className="text-foreground font-normal text-base py-4">
                    This week saw significant debate on healthcare reform, with Liberal Democrat MPs making strong interventions on NHS funding and mental health services. Sarah Green led a powerful contribution on rural healthcare access, while Ed Davey challenged the government on waiting times. The party also raised concerns about education funding cuts and local government financing, with multiple MPs highlighting the impact on their constituencies.
                </p>
                <span className="text-muted-foreground font-normal text-sm font-sans py-8">
                    Main topics
                </span>
                <div className="flex flex-wrap gap-2 pt-2">
                    <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
                        Climate Action
                    </Badge>
                    <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
                        Social Care
                    </Badge>
                    <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
                        Housing Affordability
                    </Badge>
                    <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
                        Mental Health
                    </Badge>
                    <Badge className="text-xs font-sans bg-slate-200 text-primary rounded">
                        Education Reform
                    </Badge>
                </div>
            </div>

            <div className="pt-4">
                <span className="text-muted-foreground font-normal text-sm font-sans">
                    Showing {paginatedSummaries.length} of {allSummaries.length} summaries
                </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {paginatedSummaries.map((summary, index) => renderCard(summary, startIndex + index))}
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
                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                    }
                                }}
                                className={`[&>span]:hidden ${currentPage === 1 ? "pointer-events-none opacity-50" : ""}`}
                            />
                        </PaginationItem>

                        {/* Page Numbers */}
                        {(() => {
                            const pages: (number | 'ellipsis')[] = [];
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
                                    pages.push('ellipsis');
                                    pages.push(totalPages);
                                } else if (currentPage >= totalPages - 3) {
                                    // Near the end: 1 ... (n-4) (n-3) (n-2) (n-1) n
                                    pages.push('ellipsis');
                                    for (let i = totalPages - 4; i <= totalPages; i++) {
                                        pages.push(i);
                                    }
                                } else {
                                    // In the middle: 1 ... (current-1) current (current+1) ... last
                                    pages.push('ellipsis');
                                    for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                                        pages.push(i);
                                    }
                                    pages.push('ellipsis');
                                    pages.push(totalPages);
                                }
                            }

                            return pages.map((item, index) => {
                                if (item === 'ellipsis') {
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
                                                window.scrollTo({ top: 0, behavior: 'smooth' });
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
                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                    }
                                }}
                                className={`[&>span]:hidden ${currentPage === totalPages ? "pointer-events-none opacity-50" : ""}`}
                            />
                        </PaginationItem>
                    </PaginationContent>
                </Pagination>
            )}
        </div>
    );
}

