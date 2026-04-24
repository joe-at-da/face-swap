import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { getPostizOAuthUrl } from "@/services/postiz/postizApi";

// Force this route to use Node.js runtime for postgres compatibility
export const runtime = 'nodejs';

const POSTIZ_API_URL = process.env.POSTIZ_API_URL!;

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const platform = searchParams.get("platform");

    if (!platform) {
      return new NextResponse("Platform parameter required", { status: 400 });
    }

    // Get authenticated user
    const supabase = await createSupabaseServerClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return new NextResponse("Authentication required", { status: 401 });
    }

    // Get Postiz credentials
    const { data: userRole, error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .select("postiz_email, postiz_password")
      .eq("user_id", user.id)
      .single();

    if (
      userRoleError ||
      !userRole?.postiz_email ||
      !userRole?.postiz_password
    ) {
      return new NextResponse("Postiz account not found", { status: 404 });
    }

    // Get OAuth URL for the platform
    const oauthResult = await getPostizOAuthUrl(
      userRole.postiz_email,
      userRole.postiz_password,
      platform
    );

    if (oauthResult.error || !oauthResult.data) {
      return new NextResponse(
        oauthResult.error || "Failed to get OAuth URL",
        {
          status: 500,
        }
      );
    }

    // Return HTML that logs into Postiz via hidden iframe, then redirects
    const html = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Connecting to ${platform}...</title>
          <style>
            body {
              font-family: system-ui, -apple-system, sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
              margin: 0;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              color: white;
            }
            .container {
              text-align: center;
              padding: 2rem;
            }
            .spinner {
              border: 3px solid rgba(255, 255, 255, 0.3);
              border-radius: 50%;
              border-top: 3px solid white;
              width: 40px;
              height: 40px;
              animation: spin 1s linear infinite;
              margin: 20px auto;
            }
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
            h2 { margin: 0 0 10px 0; }
            p { margin: 5px 0; opacity: 0.9; }
            #loginIframe { display: none; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="spinner"></div>
            <h2>Connecting to ${platform}</h2>
            <p>Setting up authentication...</p>
          </div>

          <iframe id="loginIframe" name="loginIframe"></iframe>

          <form id="loginForm" action="${POSTIZ_API_URL}auth/login" method="POST" target="loginIframe" style="display: none;">
            <input type="hidden" name="email" value="${userRole.postiz_email}" />
            <input type="hidden" name="password" value="${userRole.postiz_password}" />
            <input type="hidden" name="provider" value="LOCAL" />
            <input type="hidden" name="providerToken" value="" />
          </form>

          <script>
            // Submit login form to hidden iframe (sets cookies for Postiz domain)
            setTimeout(() => {
              document.getElementById('loginForm').submit();
            }, 500);

            // After login form submits, redirect to OAuth URL
            // Give it time to set cookies, then redirect
            setTimeout(() => {
              window.location.href = "${oauthResult.data}";
            }, 2000);
          </script>
        </body>
      </html>
    `;

    return new NextResponse(html, {
      headers: {
        "Content-Type": "text/html; charset=utf-8",
      },
    });
  } catch (error) {
    console.error("OAuth start error:", error);

    const errorHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Connection Error</title>
          <style>
            body {
              font-family: system-ui, -apple-system, sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
              margin: 0;
              background: #f5f5f5;
            }
            .error {
              background: white;
              padding: 2rem;
              border-radius: 8px;
              box-shadow: 0 2px 10px rgba(0,0,0,0.1);
              max-width: 400px;
              text-align: center;
            }
            h2 { color: #dc2626; margin: 0 0 10px 0; }
            p { color: #666; }
            button {
              margin-top: 1rem;
              padding: 0.5rem 1rem;
              background: #3b82f6;
              color: white;
              border: none;
              border-radius: 4px;
              cursor: pointer;
            }
            button:hover { background: #2563eb; }
          </style>
        </head>
        <body>
          <div class="error">
            <h2>Connection Failed</h2>
            <p>${error instanceof Error ? error.message : "An error occurred"}</p>
            <button onclick="window.close()">Close Window</button>
          </div>
        </body>
      </html>
    `;

    return new NextResponse(errorHtml, {
      status: 500,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
      },
    });
  }
}
