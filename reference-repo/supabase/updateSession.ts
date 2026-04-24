import "server-only";
import { getErrorMessage } from "@/lib/getErrorMessage";
import { NextRequest, NextResponse } from "next/server";
import "server-only";
import { createServerClient } from "@supabase/ssr";
import { Database } from "@/supabaseTypes";
import { serverRouteProtection } from "@/stores/utils/serverAuth";
import { SUPABASE_COOKIE_NAME } from "./cookieConfig";

export const updateSession = async (request: NextRequest) => {
  try {
    let response = NextResponse.next({
      request: {
        headers: request.headers,
      },
    });

    const currentPathname = request.nextUrl.pathname;
    if (
      currentPathname.startsWith("/api") ||
      currentPathname.startsWith("/auth")
    ) {
      return response;
    }

    // Use SUPABASE_URL (internal Docker URL) for better performance.
    // Cookie name is set explicitly via cookieOptions to match the browser client.
    const supabase = createServerClient<Database>(
      process.env.SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll();
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value }) =>
              request.cookies.set(name, value)
            );
            response = NextResponse.next({
              request,
            });
            cookiesToSet.forEach(({ name, value, options }) =>
              response.cookies.set(name, value, options)
            );
          },
        },
        cookieOptions: {
          name: SUPABASE_COOKIE_NAME,
        },
      }
    );

    const {
      data: { user },
    } = await supabase.auth.getUser();

    // Use centralized route protection logic
    if (!serverRouteProtection.canAccessRoute(currentPathname, user)) {
      const redirectUrl = serverRouteProtection.getRedirectUrl(currentPathname, user);
      if (redirectUrl) {
        console.log(`User cannot access ${currentPathname}, redirecting to ${redirectUrl}`);
        return NextResponse.redirect(new URL(redirectUrl, request.url));
      }
    }

    return response;
  } catch (error) {
    const message = getErrorMessage(error);
    console.error("error updating session", message);
    return NextResponse.next({
      request: {
        headers: request.headers,
      },
    });
  }
};
