import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { NextResponse } from "next/server";
import { ErrorLogger } from "@/lib/errorLogger";
import { finalizePostAuth } from "@/lib/auth/post-auth-finalization";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  // Use NEXT_PUBLIC_FRONTEND_URL in production, fallback to origin for local dev
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || origin;

  if (code) {
    const supabase = await createSupabaseServerClient();
    const { error, data } = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      ErrorLogger.logAuthError(
        error,
        "exchangeCodeForSession",
        undefined,
        "/auth/callback",
      );
      return NextResponse.redirect(
        `${baseUrl}/signin?error=auth_callback_error`,
      );
    }

    if (data.user) {
      try {
        const result = await finalizePostAuth(data.user, supabase);

        if (!result.ok) {
          return NextResponse.redirect(
            `${baseUrl}${result.redirectPath}?error=${result.errorCode}`,
          );
        }

        return NextResponse.redirect(`${baseUrl}${result.redirectTo}`);
      } catch (err) {
        ErrorLogger.logError(
          err instanceof Error ? err : new Error(String(err)),
          { action: "finalizePostAuth", feature: "auth" },
        );
        return NextResponse.redirect(
          `${baseUrl}/signin?error=auth_callback_error`,
        );
      }
    }
  }

  // Return to signin page if there's an error
  ErrorLogger.logAuthError(
    new Error("Auth callback: no code provided or no user data"),
    "auth_callback",
    undefined,
    "/auth/callback",
  );
  return NextResponse.redirect(`${baseUrl}/signin?error=auth_callback_error`);
}
