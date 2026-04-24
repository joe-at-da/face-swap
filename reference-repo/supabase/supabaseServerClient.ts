import "server-only";

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { Database } from "@/supabaseTypes";
import { SUPABASE_COOKIE_NAME } from "./cookieConfig";

export const createSupabaseServerClient = async () => {
  const cookieStore = await cookies();
  // Use SUPABASE_URL (internal Docker URL) for better performance.
  // Cookie name is set explicitly via cookieOptions to match the browser client.
  return createServerClient<Database>(
    process.env.SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, { ...options, path: "/" });
            });
          } catch (error) {
            console.error(
              "Error setting cookies probably was called from a server component",
              error,
            );
          }
        },
      },
      cookieOptions: {
        name: SUPABASE_COOKIE_NAME,
      },
    },
  );
};
