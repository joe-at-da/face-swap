import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { postizDb } from "@/services/postiz/postizDb";

export const runtime = "nodejs";

interface YouTubeChannel {
  id: string;
  snippet: {
    title: string;
    customUrl?: string;
    thumbnails?: {
      default?: {
        url?: string;
      };
    };
  };
  statistics?: {
    subscriberCount?: string;
  };
}

interface YouTubeChannelsResponse {
  items?: YouTubeChannel[];
  error?: {
    message?: string;
  };
}

/**
 * GET /api/oauth/youtube/integration
 * Fetches the current user's pending YouTube integration (inBetweenSteps=true)
 * and returns available channels from YouTube Data API.
 *
 * @param integrationId - Optional query param to check a specific integration's status
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const integrationId = searchParams.get("integrationId");
    // Get authenticated user
    const supabase = await createSupabaseServerClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Get Postiz credentials
    const { data: userRole } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_password")
      .eq("user_id", user.id)
      .single();

    if (!userRole?.postiz_email || !userRole?.postiz_password) {
      return NextResponse.json(
        { error: "Postiz account not found" },
        { status: 404 }
      );
    }

    // Find YouTube integration - either by specific ID or any pending one
    const integrations = integrationId
      ? await postizDb`
          SELECT i.id, i.name, i.token, i."inBetweenSteps", i."providerIdentifier"
          FROM "Integration" i
          INNER JOIN "UserOrganization" uo ON i."organizationId" = uo."organizationId"
          INNER JOIN "User" u ON uo."userId" = u.id
          WHERE u.email = ${userRole.postiz_email}
            AND i."providerIdentifier" = 'youtube'
            AND i.id = ${integrationId}
            AND i."deletedAt" IS NULL
          LIMIT 1
        `
      : await postizDb`
          SELECT i.id, i.name, i.token, i."inBetweenSteps", i."providerIdentifier"
          FROM "Integration" i
          INNER JOIN "UserOrganization" uo ON i."organizationId" = uo."organizationId"
          INNER JOIN "User" u ON uo."userId" = u.id
          WHERE u.email = ${userRole.postiz_email}
            AND i."providerIdentifier" = 'youtube'
            AND i."inBetweenSteps" = true
            AND i."deletedAt" IS NULL
          ORDER BY i."createdAt" DESC
          LIMIT 1
        `;

    if (integrations.length === 0) {
      return NextResponse.json({
        error: integrationId
          ? "YouTube integration not found"
          : "No pending YouTube integration found",
        inBetweenSteps: false,
      });
    }

    const integration = integrations[0];

    // If integration is complete (inBetweenSteps=false), no need to fetch channels
    if (!integration.inBetweenSteps) {
      return NextResponse.json({
        id: integration.id,
        inBetweenSteps: false,
      });
    }

    // Integration needs channel selection - fetch available channels
    const channelsResponse = await fetch(
      `https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true&access_token=${integration.token}`
    );
    const channelsData: YouTubeChannelsResponse = await channelsResponse.json();

    if (channelsData.error) {
      console.error("YouTube Data API error:", channelsData.error);
      return NextResponse.json(
        {
          error:
            channelsData.error.message || "Failed to fetch YouTube channels",
          inBetweenSteps: true, // Include state so share-dialog blocks correctly
        },
        { status: 500 }
      );
    }

    // Transform channels to a simpler format
    const channels = (channelsData.items || []).map((channel) => ({
      id: channel.id,
      name: channel.snippet.title,
      username: channel.snippet.customUrl,
      picture: channel.snippet.thumbnails?.default?.url,
      subscriberCount: channel.statistics?.subscriberCount,
    }));

    return NextResponse.json({
      id: integration.id,
      inBetweenSteps: true,
      channels,
    });
  } catch (error) {
    console.error("Error fetching YouTube integration:", error);
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "An error occurred",
      },
      { status: 500 }
    );
  }
}
