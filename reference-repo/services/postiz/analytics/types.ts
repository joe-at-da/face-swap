export type SupportedAnalyticsPlatform = "x" | "facebook" | "youtube";
export type AnalyticsDateRange = 7 | 30 | 90;

export type AnalyticsView =
  | { kind: "all" }
  | { kind: "channel"; integrationId: string };

export type AnalyticsChannelSummary = {
  integrationId: string;
  organizationId: string;
  platform: SupportedAnalyticsPlatform;
  label: string;
  avatarUrl: string | null;
};

export type ChannelAnalyticsPoint = {
  date: string;
  total: number;
};

export type ChannelAnalyticsMetric = {
  key: string;
  label: string;
  points: ChannelAnalyticsPoint[];
  average: boolean;
  percentageChange: number | null;
  totalValue: number;
  totalDisplay: string;
};

export type ChannelAnalyticsDto = {
  kind: "channel";
  channel: AnalyticsChannelSummary;
  range: AnalyticsDateRange;
  metrics: ChannelAnalyticsMetric[];
};

export type AllChannelsAnalyticsDto = {
  kind: "all";
  range: AnalyticsDateRange;
  channelCount: number;
  metrics: ChannelAnalyticsMetric[];
  partialFailures: number;
};

export type AnalyticsEmptyState =
  | "no_postiz_account"
  | "no_supported_channels"
  | "no_data";

export type AnalyticsErrorState = "upstream_unavailable";

export type AnalyticsPageData = {
  range: AnalyticsDateRange;
  channels: AnalyticsChannelSummary[];
  view: AnalyticsView;
  analytics: ChannelAnalyticsDto | AllChannelsAnalyticsDto | null;
  emptyState: AnalyticsEmptyState | null;
  errorState: AnalyticsErrorState | null;
};

export type ParsedAnalyticsSearchParams = {
  range: AnalyticsDateRange;
  integrationId?: string;
  shouldRedirect: boolean;
};

export type PostizSessionContext = {
  cookieHeader: string;
  source: "live" | "fixture";
};

export type AnalyticsFixtureScenario =
  | "happy"
  | "no_supported_channels"
  | "empty_channel";

export type AnalyticsFixture = {
  channels: AnalyticsChannelSummary[];
  metricsByIntegrationId: Record<
    string,
    Array<{
      label: string;
      data: ChannelAnalyticsPoint[];
      average?: boolean;
      percentageChange?: number | null;
    }>
  >;
};
