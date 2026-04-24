import { TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChannelAnalyticsMetric } from "@/services/postiz/analytics/types";
import { AnalyticsChart } from "./analytics-chart";

type ChannelAnalyticsCardProps = {
  metric: ChannelAnalyticsMetric;
};

function ChangeIndicator({
  average,
  percentageChange,
}: Pick<ChannelAnalyticsMetric, "average" | "percentageChange">) {
  if (percentageChange === null || percentageChange === 0) {
    return null;
  }

  const positive = percentageChange > 0;
  const Icon = positive ? TrendingUp : TrendingDown;

  return (
    <div
      className={
        positive
          ? "flex items-center gap-1 text-emerald-600 dark:text-emerald-400"
          : "flex items-center gap-1 text-rose-600 dark:text-rose-400"
      }
    >
      <Icon className="h-4 w-4" />
      <span className="text-sm font-medium">
        {Math.abs(percentageChange).toFixed(1)}
        {average ? "pp" : "%"}
      </span>
    </div>
  );
}

export function ChannelAnalyticsCard({
  metric,
}: ChannelAnalyticsCardProps) {
  const showChart = metric.points.length > 1;

  return (
    <Card className="h-full">
      <CardHeader className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <CardTitle className="text-base">{metric.label}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {metric.average ? "Average across the selected range" : "Total across the selected range"}
            </p>
          </div>
          <ChangeIndicator
            average={metric.average}
            percentageChange={metric.percentageChange}
          />
        </div>
        <div className="text-4xl font-semibold tracking-tight">
          {metric.totalDisplay}
        </div>
      </CardHeader>
      <CardContent>
        {showChart ? (
          <AnalyticsChart label={metric.label} points={metric.points} />
        ) : (
          <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
            Only one data point is available for this metric in the selected range.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
