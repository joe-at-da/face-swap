import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { postizDb } from "@/services/postiz/postizDb";

export const runtime = "nodejs";

interface FacebookPage {
  id: string;
  name: string;
  username?: string;
  picture?: {
    data?: {
      url?: string;
    };
  };
}

interface FacebookPagesResponse {
  data?: FacebookPage[];
  error?: {
    message?: string;
  };
}

/**
 * GET /api/oauth/facebook/integration
 * Fetches the current user's pending Facebook integration (inBetweenSteps=true)
 * and returns available pages from Facebook Graph API.
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

    // Find Facebook integration - either by specific ID or any pending one
    const integrations = integrationId
      ? await postizDb`
          SELECT i.id, i.name, i.token, i."inBetweenSteps", i."providerIdentifier"
          FROM "Integration" i
          INNER JOIN "UserOrganization" uo ON i."organizationId" = uo."organizationId"
          INNER JOIN "User" u ON uo."userId" = u.id
          WHERE u.email = ${userRole.postiz_email}
            AND i."providerIdentifier" = 'facebook'
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
            AND i."providerIdentifier" = 'facebook'
            AND i."inBetweenSteps" = true
            AND i."deletedAt" IS NULL
          ORDER BY i."createdAt" DESC
          LIMIT 1
        `;

    if (integrations.length === 0) {
      return NextResponse.json({
        error: integrationId
          ? "Facebook integration not found"
          : "No pending Facebook integration found",
        inBetweenSteps: false,
      });
    }

    const integration = integrations[0];

    // If integration is complete (inBetweenSteps=false), no need to fetch pages
    if (!integration.inBetweenSteps) {
      return NextResponse.json({
        id: integration.id,
        inBetweenSteps: false,
      });
    }

    // Integration needs page selection - fetch available pages
    const pagesResponse = await fetch(
      `https://graph.facebook.com/v20.0/me/accounts?fields=id,username,name,picture.type(large)&access_token=${integration.token}`
    );
    const pagesData: FacebookPagesResponse = await pagesResponse.json();

    if (pagesData.error) {
      console.error("Facebook Graph API error:", pagesData.error);
      return NextResponse.json(
        {
          error:
            pagesData.error.message || "Failed to fetch Facebook pages",
          inBetweenSteps: true, // Include state so share-dialog blocks correctly
        },
        { status: 500 }
      );
    }

    return NextResponse.json({
      id: integration.id,
      inBetweenSteps: true,
      pages: pagesData.data || [],
    });
  } catch (error) {
    console.error("Error fetching Facebook integration:", error);
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "An error occurred",
      },
      { status: 500 }
    );
  }
}
