import "server-only";

import { cache } from "react";
import { z } from "zod";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { ErrorLogger } from "@/lib/errorLogger";
import { AnalyticsServiceError, isAnalyticsServiceError } from "./errors";
import { getAnalyticsFixture } from "./fixtures";
import { fetchPostizAnalytics, loginToPostiz } from "./client";
import type {
  AnalyticsChannelSummary,
  AnalyticsDateRange,
  AnalyticsFixtureScenario,
  AnalyticsPageData,
  AnalyticsView,
  ChannelAnalyticsMetric,
  PostizSessionContext,
} from "./types";

const SUPPORTED_ANALYTICS_PLATFORMS = ["x", "facebook", "youtube"] as const;
const supportedPlatformSchema = z.enum(SUPPORTED_ANALYTICS_PLATFORMS);

const postizChannelRowSchema = z.object({
  integrationId: z.string(),
  organizationId: z.string(),
  platform: z.string(),
  label: z.string(),
  avatarUrl: z.string().nullable(),
});

const METRIC_SORT_ORDER = [
  "impression",
  "like",
  "retweet",
  "reply",
  "quote",
  "bookmark",
  "views",
  "watch_time",
] as const;

function normalizeMetricLabel(label: string): string {
  return label
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getMetricSortIndex(key: string): number {
  const normalizedKey = key.split("::")[0] ?? key;
  const index = (METRIC_SORT_ORDER as readonly string[]).indexOf(normalizedKey);
  return index === -1 ? METRIC_SORT_ORDER.length : index;
}

function sortMetricsByCanonicalOrder(
  metrics: ChannelAnalyticsMetric[]
): ChannelAnalyticsMetric[] {
  return [...metrics].sort((left, right) => {
    const leftIndex = getMetricSortIndex(left.key);
    const rightIndex = getMetricSortIndex(right.key);
    if (leftIndex !== rightIndex) return leftIndex - rightIndex;
    return left.label.localeCompare(right.label);
  });
}

const getPostizCredentials = cache(async (userId: string) => {
  const { data, error } = await supabaseAdminClient
    .from("user_roles")
    .select("postiz_email, postiz_password")
    .eq("user_id", userId)
    .maybeSingle();

  if (error) {
    ErrorLogger.logDatabaseError(
      error,
      "getPostizCredentials",
      "user_roles",
      userId
    );
    throw new AnalyticsServiceError(
      "upstream_unavailable",
      "Failed to load Postiz credentials",
      error
    );
  }

  return data ?? { postiz_email: null, postiz_password: null };
});

function getFixtureScenario(
  postizEmail: string | null | undefined
): AnalyticsFixtureScenario | null {
  if (
    process.env.NODE_ENV === "production" ||
    !postizEmail ||
    !postizEmail.startsWith("fixture:")
  ) {
    return null;
  }

  const scenario = postizEmail.replace("fixture:", "").trim();
  if (scenario === "no-supported-channels") {
    return "no_supported_channels";
  }
  if (scenario === "empty-channel") {
    return "empty_channel";
  }

  return "happy";
}

export const getEligibleAnalyticsChannels = cache(
  async (
    userId: string
  ): Promise<{
    channels: AnalyticsChannelSummary[];
    fixtureScenario: AnalyticsFixtureScenario | null;
    hasCredentials: boolean;
  }> => {
    const credentials = await getPostizCredentials(userId);
    const fixtureScenario = getFixtureScenario(credentials.postiz_email);

    if (fixtureScenario) {
      return {
        channels: getAnalyticsFixture(fixtureScenario, 7).channels,
        fixtureScenario,
        hasCredentials: true,
      };
    }

    if (!credentials.postiz_email || !credentials.postiz_password) {
      return { channels: [], fixtureScenario: null, hasCredentials: false };
    }

    try {
      const { postizDb } = await import("@/services/postiz/postizDb");
      const rawChannels = await postizDb`
        SELECT
          i.id AS "integrationId",
          i."organizationId" AS "organizationId",
          i."providerIdentifier" AS "platform",
          COALESCE(NULLIF(i.name, ''), i.profile, i."providerIdentifier") AS "label",
          NULLIF(i.picture, '') AS "avatarUrl"
        FROM "Integration" i
        INNER JOIN "UserOrganization" uo ON i."organizationId" = uo."organizationId"
        INNER JOIN "User" u ON uo."userId" = u.id
        WHERE u.email = ${credentials.postiz_email}
          AND uo.disabled = false
          AND i.disabled = false
          AND i."deletedAt" IS NULL
          AND i."providerIdentifier" IN ${postizDb(SUPPORTED_ANALYTICS_PLATFORMS)}
          AND (
            i."providerIdentifier" = 'x'
            OR i."inBetweenSteps" IS NOT TRUE
          )
        ORDER BY i."providerIdentifier" ASC, i.name ASC, i.id ASC
      `;

      return {
        channels: rawChannels.map((row) => {
          const parsed = postizChannelRowSchema.parse(row);
          return {
            ...parsed,
            platform: supportedPlatformSchema.parse(parsed.platform),
          };
        }),
        fixtureScenario: null,
        hasCredentials: true,
      };
    } catch (error) {
      ErrorLogger.logError(
        error instanceof Error ? error : new Error(String(error)),
        {
          userId,
          component: "getEligibleAnalyticsChannels",
          feature: "social_analytics",
        }
      );
      throw new AnalyticsServiceError(
        "upstream_unavailable",
        "Failed to fetch channel inventory from Postiz DB",
        error instanceof Error ? error : undefined
      );
    }
  }
);


const getPostizSessionContext = cache(
  async (userId: string): Promise<PostizSessionContext> => {
    const credentials = await getPostizCredentials(userId);
    const fixtureScenario = getFixtureScenario(credentials.postiz_email);

    if (fixtureScenario) {
      return {
        cookieHeader: `fixture-session=${fixtureScenario}`,
        source: "fixture",
      };
    }

    if (!credentials.postiz_email || !credentials.postiz_password) {
      throw new AnalyticsServiceError(
        "not_found",
        "Postiz account is not configured"
      );
    }

    const startedAt = performance.now();
    const session = await loginToPostiz(
      credentials.postiz_email,
      credentials.postiz_password
    );

    ErrorLogger.logEvent("postiz_login_ms", {
      userId,
      component: "postiz_analytics",
      action: "postiz_login",
      feature: "social_analytics",
      additionalContext: {
        durationMs: Math.round(performance.now() - startedAt),
      },
    });

    return {
      cookieHeader: session.cookieHeader,
      source: "live",
    };
  }
);

function buildMetricKey(label: string, average: boolean): string {
  return `${label.trim().toLowerCase()}::${average ? "avg" : "sum"}`;
}

function formatAnalyticsTotal(
  points: Array<{ total: number }>,
  average: boolean
): { totalValue: number; totalDisplay: string } {
  const rawTotal = points.reduce((sum, point) => sum + point.total, 0);
  const totalValue =
    average && points.length > 0 ? rawTotal / points.length : rawTotal;

  if (average) {
    return {
      totalValue,
      totalDisplay: `${totalValue.toFixed(2)}%`,
    };
  }

  return {
    totalValue,
    totalDisplay: new Intl.NumberFormat().format(Math.round(totalValue)),
  };
}

function computePercentageChange(
  points: Array<{ total: number }>,
  average: boolean
): number | null {
  if (points.length < 2) {
    return null;
  }

  const first = points[0]?.total ?? 0;
  const last = points[points.length - 1]?.total ?? 0;

  if (average) {
    return Number((last - first).toFixed(1));
  }

  if (first === 0) {
    return null;
  }

  return Number((((last - first) / Math.abs(first)) * 100).toFixed(1));
}

function normalizeAnalyticsMetrics(
  metrics: Array<{
    label: string;
    data: Array<{ date: string; total: number }>;
    average?: boolean;
    percentageChange?: number | null;
  }>
): ChannelAnalyticsMetric[] {
  return metrics.map((metric) => {
    const average = metric.average === true;
    const { totalValue, totalDisplay } = formatAnalyticsTotal(
      metric.data,
      average
    );

    return {
      key: buildMetricKey(metric.label, average),
      label: normalizeMetricLabel(metric.label),
      points: metric.data,
      average,
      percentageChange: metric.percentageChange ?? null,
      totalValue,
      totalDisplay,
    };
  });
}

async function getChannelAnalyticsMetrics(
  userId: string,
  integrationId: string,
  range: AnalyticsDateRange,
  fixtureScenario: AnalyticsFixtureScenario | null
): Promise<ChannelAnalyticsMetric[]> {
  const startedAt = performance.now();

  try {
    if (fixtureScenario) {
      const fixture = getAnalyticsFixture(fixtureScenario, range);
      return sortMetricsByCanonicalOrder(
        normalizeAnalyticsMetrics(
          fixture.metricsByIntegrationId[integrationId] ?? []
        )
      );
    }

    const session = await getPostizSessionContext(userId);
    const parsed = await fetchPostizAnalytics(session, integrationId, range);
    return sortMetricsByCanonicalOrder(normalizeAnalyticsMetrics(parsed));
  } finally {
    ErrorLogger.logEvent("postiz_analytics_fetch_ms", {
      userId,
      component: "postiz_analytics",
      action: "fetch_channel_analytics",
      feature: "social_analytics",
      additionalContext: {
        integrationId,
        durationMs: Math.round(performance.now() - startedAt),
      },
    });
  }
}

function aggregateAllChannelMetrics(
  channelMetrics: ChannelAnalyticsMetric[]
): ChannelAnalyticsMetric[] {
  const aggregateMap = new Map<
    string,
    {
      label: string;
      average: boolean;
      points: Map<string, { sum: number; count: number }>;
    }
  >();

  for (const metric of channelMetrics) {
    const existing = aggregateMap.get(metric.key) ?? {
      label: metric.label,
      average: metric.average,
      points: new Map<string, { sum: number; count: number }>(),
    };

    for (const point of metric.points) {
      const prev = existing.points.get(point.date) ?? { sum: 0, count: 0 };
      existing.points.set(point.date, {
        sum: prev.sum + point.total,
        count: prev.count + 1,
      });
    }

    aggregateMap.set(metric.key, existing);
  }

  const unsorted = Array.from(aggregateMap.entries()).map(([key, metric]) => {
    const points = Array.from(metric.points.entries())
      .map(([date, { sum, count }]) => ({
        date,
        total: metric.average && count > 0 ? sum / count : sum,
      }))
      .sort((left, right) => left.date.localeCompare(right.date));
    const { totalValue, totalDisplay } = formatAnalyticsTotal(
      points,
      metric.average
    );

    return {
      key,
      label: metric.label,
      points,
      average: metric.average,
      percentageChange: computePercentageChange(points, metric.average),
      totalValue,
      totalDisplay,
    };
  });

  return sortMetricsByCanonicalOrder(unsorted);
}

export async function getAnalyticsPageData(
  userId: string,
  view: AnalyticsView,
  range: AnalyticsDateRange
): Promise<AnalyticsPageData> {
  // Pre-warm Postiz session in parallel with channel query — cache() deduplicates
  // the session for subsequent per-channel fetches within this render
  let channelResult: Awaited<ReturnType<typeof getEligibleAnalyticsChannels>>;
  try {
    [channelResult] = await Promise.all([
      getEligibleAnalyticsChannels(userId),
      getPostizSessionContext(userId).catch(() => null),
    ]);
  } catch (error) {
    if (isAnalyticsServiceError(error) && error.code === "upstream_unavailable") {
      return {
        range,
        channels: [],
        view: { kind: "all" },
        analytics: null,
        emptyState: null,
        errorState: "upstream_unavailable",
      };
    }
    throw error;
  }
  const { channels, fixtureScenario, hasCredentials } = channelResult;

  if (!hasCredentials) {
    return {
      range,
      channels: [],
      view: { kind: "all" },
      analytics: null,
      emptyState: "no_postiz_account",
      errorState: null,
    };
  }

  if (channels.length === 0) {
    return {
      range,
      channels: [],
      view: { kind: "all" },
      analytics: null,
      emptyState: "no_supported_channels",
      errorState: null,
    };
  }

  if (view.kind === "channel") {
    const selectedChannel = channels.find(
      (channel) => channel.integrationId === view.integrationId
    );

    if (!selectedChannel) {
      throw new AnalyticsServiceError(
        "not_found",
        "Selected analytics channel is no longer available"
      );
    }

    try {
      const metrics = await getChannelAnalyticsMetrics(
        userId,
        selectedChannel.integrationId,
        range,
        fixtureScenario
      );

      if (metrics.length === 0) {
        return {
          range,
          channels,
          view,
          analytics: null,
          emptyState: "no_data",
          errorState: null,
        };
      }

      return {
        range,
        channels,
        view,
        analytics: {
          kind: "channel",
          channel: selectedChannel,
          range,
          metrics,
        },
        emptyState: null,
        errorState: null,
      };
    } catch (error) {
      if (isAnalyticsServiceError(error) && error.code !== "upstream_unavailable") {
        throw error;
      }

      ErrorLogger.logError(
        error instanceof Error ? error : new Error(String(error)),
        {
          userId,
          component: "getAnalyticsPageData:channel",
          feature: "social_analytics",
          additionalContext: { integrationId: selectedChannel.integrationId },
        }
      );

      return {
        range,
        channels,
        view,
        analytics: null,
        emptyState: null,
        errorState: "upstream_unavailable",
      };
    }
  }

  const startedAt = performance.now();
  const results = await Promise.allSettled(
    channels.map((channel) =>
      getChannelAnalyticsMetrics(
        userId,
        channel.integrationId,
        range,
        fixtureScenario
      ).then((metrics) => ({ channel, metrics }))
    )
  );

  const fulfilled = results.filter(
    (
      result
    ): result is PromiseFulfilledResult<{
      channel: AnalyticsChannelSummary;
      metrics: ChannelAnalyticsMetric[];
    }> => result.status === "fulfilled"
  );
  const partialFailures = results.length - fulfilled.length;
  const successfulMetrics = fulfilled.flatMap((result) => result.value.metrics);

  ErrorLogger.logEvent("postiz_analytics_aggregation_ms", {
    userId,
    component: "postiz_analytics",
    action: "aggregate_all_channels",
    feature: "social_analytics",
    additionalContext: {
      durationMs: Math.round(performance.now() - startedAt),
      partialFailures,
    },
  });

  if (partialFailures > 0) {
    ErrorLogger.logEvent("postiz_analytics_partial_failures", {
      userId,
      component: "postiz_analytics",
      action: "aggregate_all_channels",
      feature: "social_analytics",
      additionalContext: {
        partialFailures,
        totalChannels: channels.length,
      },
    });
  }

  const allChannelsFailed = partialFailures === results.length;

  if (allChannelsFailed) {
    return {
      range,
      channels,
      view,
      analytics: null,
      emptyState: null,
      errorState: "upstream_unavailable",
    };
  }

  const aggregatedMetrics = aggregateAllChannelMetrics(successfulMetrics);

  if (aggregatedMetrics.length === 0) {
    return {
      range,
      channels,
      view,
      analytics: null,
      emptyState: partialFailures > 0 ? null : "no_data",
      errorState: partialFailures > 0 ? "upstream_unavailable" : null,
    };
  }

  return {
    range,
    channels,
    view,
    analytics: {
      kind: "all",
      range,
      channelCount: fulfilled.filter((r) => r.value.metrics.length > 0).length,
      metrics: aggregatedMetrics,
      partialFailures,
    },
    emptyState: null,
    errorState: null,
  };
}
