import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type {
  AllChannelsAnalyticsDto,
  ChannelAnalyticsDto,
  SupportedAnalyticsPlatform,
} from "@/services/postiz/analytics/types";
import { ChannelAnalyticsCard } from "./channel-analytics-card";
import {
  ANALYTICS_PLATFORM_COLORS,
  ANALYTICS_PLATFORM_ICONS,
  getPlatformLabel,
} from "./platform-utils";

type AnalyticsPanelProps = {
  analytics: ChannelAnalyticsDto | AllChannelsAnalyticsDto;
};

function PlatformBadge({ platform }: { platform: SupportedAnalyticsPlatform }) {
  const Icon = ANALYTICS_PLATFORM_ICONS[platform];
  const color = ANALYTICS_PLATFORM_COLORS[platform];
  return (
    <Badge variant="outline" className="gap-1.5">
      <Icon className={`h-3.5 w-3.5 ${color}`} />
      {getPlatformLabel(platform)}
    </Badge>
  );
}

export function AnalyticsPanel({ analytics }: AnalyticsPanelProps) {
  const title =
    analytics.kind === "all"
      ? "All Channels"
      : analytics.channel.label;
  const subtitle =
    analytics.kind === "all"
      ? `${analytics.channelCount} channel${analytics.channelCount === 1 ? "" : "s"} in this rollup`
      : getPlatformLabel(analytics.channel.platform);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {analytics.kind === "channel" ? (
          <PlatformBadge platform={analytics.channel.platform} />
        ) : (
          <Badge variant="outline">App-computed overview</Badge>
        )}
      </div>

      {analytics.kind === "all" && analytics.partialFailures > 0 ? (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Some channels were unavailable</AlertTitle>
          <AlertDescription>
            {analytics.partialFailures} channel
            {analytics.partialFailures === 1 ? "" : "s"} could not be included in
            the current rollup. The rest of the overview is still available.
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {analytics.metrics.map((metric) => (
          <ChannelAnalyticsCard key={metric.key} metric={metric} />
        ))}
      </div>
    </div>
  );
}
