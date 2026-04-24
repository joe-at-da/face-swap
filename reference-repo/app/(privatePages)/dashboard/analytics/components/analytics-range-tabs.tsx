"use client";

import { useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AnalyticsDateRange } from "@/services/postiz/analytics/types";

const RANGES: AnalyticsDateRange[] = [7, 30, 90];

type AnalyticsRangeTabsProps = {
  currentRange: AnalyticsDateRange;
};

export function AnalyticsRangeTabs({
  currentRange,
}: AnalyticsRangeTabsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const handleChange = (nextValue: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("date", nextValue);

    startTransition(() => {
      router.replace(`${pathname}?${params.toString()}`);
    });
  };

  return (
    <Tabs value={String(currentRange)} onValueChange={handleChange}>
      <TabsList className={`min-h-[44px] ${isPending ? "opacity-60 pointer-events-none" : ""}`}>
        {RANGES.map((range) => (
          <TabsTrigger key={range} value={String(range)} className="min-h-[40px] px-4">
            {range} Days
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
