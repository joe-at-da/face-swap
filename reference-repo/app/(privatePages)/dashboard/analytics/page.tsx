import { redirect } from "next/navigation";
import { AlertCircle, BarChart3, Link2, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { canAccessInternalAnalytics } from "@/lib/social-analytics-access";
import { isActualMPCached, isTeamOnlyMember } from "@/lib/user-helpers";
import { parseAnalyticsSearchParams } from "@/services/postiz/analytics/schemas";
import {
  getEligibleAnalyticsChannels,
  getAnalyticsPageData,
} from "@/services/postiz/analytics/service";
import { isAnalyticsServiceError } from "@/services/postiz/analytics/errors";
import type { AnalyticsDateRange, AnalyticsPageData } from "@/services/postiz/analytics/types";
import { AnalyticsPanel } from "./components/analytics-panel";
import { AnalyticsRangeTabs } from "./components/analytics-range-tabs";
import { ChannelPicker } from "./components/channel-picker";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type DashboardAnalyticsPageProps = {
  searchParams: Promise<{
    date?: string;
    integrationId?: string;
  }>;
};

function buildAnalyticsUrl(
  range: AnalyticsDateRange,
  integrationId?: string
): string {
  const params = new URLSearchParams({
    date: String(range),
  });

  if (integrationId) {
    params.set("integrationId", integrationId);
  }

  return `/dashboard/analytics?${params.toString()}`;
}

function EmptyStateCard({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof BarChart3;
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Icon className="h-6 w-6 text-muted-foreground" />
        </div>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

export default async function DashboardAnalyticsPage({
  searchParams,
}: DashboardAnalyticsPageProps) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  const isActualMPUser = await isActualMPCached(
    user.id,
    user.email ?? "",
    supabaseAdminClient
  );
  const isUserTeamOnly = isTeamOnlyMember(user, isActualMPUser);

  if (isUserTeamOnly || !canAccessInternalAnalytics(user.email)) {
    redirect("/dashboard");
  }

  const params = parseAnalyticsSearchParams(await searchParams);
  if (params.shouldRedirect) {
    redirect(buildAnalyticsUrl(params.range, params.integrationId));
  }

  const view = params.integrationId
    ? { kind: "channel" as const, integrationId: params.integrationId }
    : { kind: "all" as const };

  let pageData: AnalyticsPageData;
  try {
    pageData = await getAnalyticsPageData(user.id, view, params.range);
  } catch (error) {
    if (isAnalyticsServiceError(error) && error.code === "not_found") {
      const inventory = await getEligibleAnalyticsChannels(user.id);
      redirect(
        buildAnalyticsUrl(params.range, inventory.channels[0]?.integrationId)
      );
    }

    throw error;
  }

  return (
    <div className="space-y-6 pt-4">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Social Analytics</h1>
        <p className="max-w-3xl text-base text-muted-foreground">
          Review Postiz-backed analytics for your connected X, Facebook, and
          YouTube channels without leaving the dashboard.
        </p>
      </div>

      {pageData.channels.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,320px)_auto] lg:items-center lg:justify-between">
          <ChannelPicker
            channels={pageData.channels}
            selectedIntegrationId={
              pageData.view.kind === "channel"
                ? pageData.view.integrationId
                : undefined
            }
          />
          <div className="flex justify-start lg:justify-end">
            <AnalyticsRangeTabs currentRange={pageData.range} />
          </div>
        </div>
      ) : null}

      {pageData.errorState === "upstream_unavailable" ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Postiz analytics is temporarily unavailable</AlertTitle>
          <AlertDescription>
            The dashboard could not load analytics from Postiz for this request.
            Retry in a minute or verify the upstream connection.
          </AlertDescription>
        </Alert>
      ) : null}

      {pageData.emptyState === "no_postiz_account" ? (
        <EmptyStateCard
          icon={ShieldAlert}
          title="Postiz isn&apos;t configured for this account"
          description="This dashboard view is available only after Postiz credentials have been saved for your personal account."
        />
      ) : null}

      {pageData.emptyState === "no_supported_channels" ? (
        <EmptyStateCard
          icon={Link2}
          title="No supported analytics channels found"
          description="Connect an X, Facebook, or YouTube account in Settings to see analytics here. Bluesky and incomplete channel selections are excluded from this view."
        />
      ) : null}

      {pageData.emptyState === "no_data" ? (
        <EmptyStateCard
          icon={BarChart3}
          title="No analytics data is available yet"
          description="The selected channel and range do not have any analytics points yet. Try a different date range or come back after the channel refreshes in Postiz."
        />
      ) : null}

      {pageData.analytics ? <AnalyticsPanel analytics={pageData.analytics} /> : null}
    </div>
  );
}
