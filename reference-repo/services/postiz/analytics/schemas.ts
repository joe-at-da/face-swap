import { z } from "zod";
import type {
  AnalyticsDateRange,
  ParsedAnalyticsSearchParams,
} from "./types";

const analyticsDateSchema = z.enum(["7", "30", "90"]);

const analyticsSearchParamsSchema = z.object({
  date: z.string().optional(),
  integrationId: z.string().optional(),
});

const postizAnalyticsMetricSchema = z.object({
  label: z.string().min(1),
  data: z.array(
    z.object({
      total: z.coerce.number(),
      date: z.string().min(1),
    })
  ),
  average: z.boolean().optional(),
  percentageChange: z.coerce.number().nullable().optional(),
});

export const postizAnalyticsResponseSchema = z.array(
  postizAnalyticsMetricSchema
);

export function parseAnalyticsSearchParams(
  raw: Record<string, string | string[] | undefined>
): ParsedAnalyticsSearchParams {
  const parsed = analyticsSearchParamsSchema.parse({
    date: Array.isArray(raw.date) ? raw.date[0] : raw.date,
    integrationId: Array.isArray(raw.integrationId)
      ? raw.integrationId[0]
      : raw.integrationId,
  });

  const dateRangeMap: Record<z.infer<typeof analyticsDateSchema>, AnalyticsDateRange> = {
    "7": 7,
    "30": 30,
    "90": 90,
  };

  const dateResult = analyticsDateSchema.safeParse(parsed.date);
  const range: AnalyticsDateRange = dateResult.success
    ? dateRangeMap[dateResult.data]
    : 7;

  const integrationId = parsed.integrationId?.trim();
  const hasValidIntegrationId =
    !!integrationId &&
    integrationId.length <= 100 &&
    /^[a-zA-Z0-9_-]+$/.test(integrationId);

  return {
    range,
    integrationId: hasValidIntegrationId ? integrationId : undefined,
    shouldRedirect:
      !dateResult.success || (!!integrationId && !hasValidIntegrationId),
  };
}
