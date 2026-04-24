"use client";

import { createBrowserClient } from "@supabase/ssr";
import { Database } from "@/supabaseTypes";
import { SUPABASE_COOKIE_NAME } from "./cookieConfig";

export const createSupabaseBrowserClient = () => {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookieOptions: {
        name: SUPABASE_COOKIE_NAME,
      },
    }
  );
};
