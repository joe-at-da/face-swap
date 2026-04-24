import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { loginUserToPostiz } from "@/services/postiz/postizApi";

export const runtime = "nodejs";

const POSTIZ_API_URL = process.env.POSTIZ_API_URL!;

/**
 * POST /api/oauth/facebook/select-page
 * Completes Facebook page selection via Postiz API.
 * Sets inBetweenSteps=false and updates the integration with the page's access token.
 */
export async function POST(request: NextRequest) {
  try {
    const { integrationId, pageId } = await request.json();

    if (!integrationId || !pageId) {
      return NextResponse.json(
        { error: "Missing required fields: integrationId and pageId" },
        { status: 400 }
      );
    }

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

    // Login to Postiz
    const loginResult = await loginUserToPostiz(
      userRole.postiz_email,
      userRole.postiz_password
    );

    if (loginResult.error || !loginResult.data) {
      console.error("Postiz login error:", loginResult.error);
      return NextResponse.json(
        { error: "Failed to authenticate with Postiz" },
        { status: 500 }
      );
    }

    const authCookie = loginResult.data;

    // Call Postiz page selection endpoint
    const response = await fetch(
      `${POSTIZ_API_URL}integrations/provider/${integrationId}/connect`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: authCookie,
        },
        body: JSON.stringify({
          state: "page-selection",
          page: pageId,
        }),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "Postiz page selection error:",
        response.status,
        errorText
      );
      return NextResponse.json(
        { error: "Failed to complete page selection" },
        { status: response.status }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error selecting Facebook page:", error);
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "An error occurred",
      },
      { status: 500 }
    );
  }
}
