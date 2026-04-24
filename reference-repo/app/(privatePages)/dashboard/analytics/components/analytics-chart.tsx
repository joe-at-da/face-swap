"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
} from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import type { ChannelAnalyticsPoint } from "@/services/postiz/analytics/types";

const MONTH_ABBR = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;

/**
 * Format a YYYY-MM-DD string without going through the Date constructor,
 * which would interpret it as UTC midnight and then display it in local time,
 * shifting the day for users in negative-UTC offsets.
 */
function formatDateLabel(value: string, includeYear = false): string {
  const [yearStr, monthStr, dayStr] = value.split("-");
  const monthIndex = Number(monthStr) - 1;
  const day = Number(dayStr);
  if (isNaN(monthIndex) || isNaN(day) || !MONTH_ABBR[monthIndex]) {
    return value;
  }
  return includeYear
    ? `${MONTH_ABBR[monthIndex]} ${day}, ${yearStr}`
    : `${MONTH_ABBR[monthIndex]} ${day}`;
}

type AnalyticsChartProps = {
  points: ChannelAnalyticsPoint[];
  label: string;
};

export function AnalyticsChart({ points, label }: AnalyticsChartProps) {
  return (
    <ChartContainer
      className="h-[170px] w-full"
      aria-label={`${label} trend chart`}
      config={{
        total: {
          label: "Total",
          color: "var(--primary)",
        },
      }}
    >
      <LineChart accessibilityLayer data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          axisLine={false}
          dataKey="date"
          minTickGap={24}
          tickFormatter={(value: string) => formatDateLabel(value)}
          tickLine={false}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              indicator="line"
              labelFormatter={(value) =>
                typeof value === "string"
                  ? formatDateLabel(value, true)
                  : String(value)
              }
            />
          }
        />
        <Line
          dataKey="total"
          dot={false}
          stroke="var(--color-total)"
          strokeWidth={2}
          type="monotone"
        />
      </LineChart>
    </ChartContainer>
  );
}
