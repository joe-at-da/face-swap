import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { loginUserToPostiz } from "@/services/postiz/postizApi";

// Force this route to use Node.js runtime
export const runtime = 'nodejs';

const POSTIZ_API_URL = process.env.POSTIZ_API_URL!;

/**
 * Server-side endpoint to handle Bluesky connection
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { service, identifier, password, timezone } = body;

    if (!service || !identifier || !password) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    // Use timezone from client, fallback to UTC (0) if not provided
    const userTimezone = timezone ?? "0";

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
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_password")
      .eq("user_id", user.id)
      .single();

    if (userRoleError) {
      console.error("Error fetching user role:", userRoleError);
      return NextResponse.json(
        { error: "Failed to fetch user data. Please try again." },
        { status: 500 }
      );
    }

    if (!userRole?.postiz_email || !userRole?.postiz_password) {
      console.error("Postiz credentials not found for user:", user.id, "userRole:", userRole);
      return NextResponse.json(
        { error: "Postiz account not set up. Please complete your profile setup first." },
        { status: 404 }
      );
    }

    // Step 1: Login to Postiz to get authentication cookie
    console.log("Logging into Postiz for Bluesky connection...");
    const loginResult = await loginUserToPostiz(
      userRole.postiz_email,
      userRole.postiz_password
    );

    if (loginResult.error || !loginResult.data) {
      console.error("Postiz login error:", loginResult.error);
      return NextResponse.json(
        { error: loginResult.error || "Failed to login to Postiz" },
        { status: 500 }
      );
    }

    const authCookie = loginResult.data;
    console.log("Successfully logged into Postiz");

    // Step 2: Encode Bluesky credentials as base64 (matching Postiz format)
    const encodedCredentials = Buffer.from(
      JSON.stringify({
        service,
        identifier,
        password,
      })
    ).toString("base64");

    // Step 3: Call Postiz Bluesky connect endpoint with encoded credentials
    // This is the POST endpoint that actually processes the authentication
    const connectUrl = `${POSTIZ_API_URL}integrations/social/bluesky/connect`;
    console.log("Calling Postiz Bluesky connect endpoint...");

    // Prepare the body - matching what the frontend sends
    const connectBody = {
      code: encodedCredentials,
      state: 'nostate', // For custom fields providers like Bluesky
      timezone: userTimezone, // Timezone offset in hours from client
    };

    const response = await fetch(connectUrl, {
      method: "POST",
      headers: {
        Cookie: authCookie,
        "Content-Type": "application/json",
        Accept: "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (compatible; Next.js)",
      },
      body: JSON.stringify(connectBody),
    });

    console.log("Postiz response status:", response.status);

    // Handle response
    const responseText = await response.text();
    console.log("Response text:", responseText);

    // Try to parse as JSON
    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = { message: responseText };
    }

    // Check if response indicates success
    // The connect endpoint returns an integration object on success
    if (response.ok && responseData?.id) {
      console.log("Bluesky integration successful! Integration ID:", responseData.id);

      return NextResponse.json(
        {
          success: true,
          message: "Bluesky account connected successfully",
          integrationId: responseData.id,
        },
        { status: 200 }
      );
    }

    // Check for specific error codes
    if (response.status === 412) {
      // Precondition failed - usually means trial limitation
      return NextResponse.json(
        { error: "This account has already been connected before. Premium subscription may be required for multiple connections." },
        { status: 412 }
      );
    }

    if (response.status === 406) {
      // Not acceptable - usually means scope issues
      const errorMsg = responseData?.msg || "Insufficient permissions to connect this account";
      return NextResponse.json(
        { error: errorMsg },
        { status: 406 }
      );
    }

    // Handle general errors with a more human-friendly message
    let errorMessage = responseData?.error || responseData?.message;
    if (!errorMessage || typeof errorMessage !== "string") {
      errorMessage = "Something went wrong connecting your Bluesky account. Please try again or contact support if this keeps happening.";
    } else if (errorMessage.toLowerCase().includes("invalid") || errorMessage.toLowerCase().includes("error")) {
      errorMessage = `Could not connect: ${errorMessage}`;
    }
    console.error("Bluesky integration error:", errorMessage, "Status:", response.status);

    // If the original response was successful (2xx) but no id was returned,
    // this indicates a business logic failure - return 500 to ensure client shows error
    const errorStatus = response.ok ? 500 : (response.status || 500);

    return NextResponse.json(
      { error: errorMessage },
      { status: errorStatus }
    );
  } catch (error) {
    console.error("Bluesky OAuth error:", error);
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "An error occurred",
      },
      { status: 500 }
    );
  }
}