import { createClient } from "@supabase/supabase-js";
import type { Database } from "@/supabaseTypes";

/**
 * Test-specific Supabase admin client.
 * Mirrors supabase/supabaseAdmin.ts but without the "server-only" import
 * that crashes in Playwright test context.
 */
let _adminClient: ReturnType<typeof createClient<Database>> | null = null;

export function createTestSupabaseAdmin() {
  if (_adminClient) return _adminClient;

  const supabaseUrl =
    process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
  const serviceKey =
    process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceKey) {
    throw new Error(
      "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY env vars for test admin client"
    );
  }

  // Safety: refuse to create admin client against non-local Supabase
  if (!supabaseUrl.includes("localhost") && !supabaseUrl.includes("127.0.0.1")) {
    throw new Error(
      `Refusing to create admin client for non-local Supabase: ${supabaseUrl}`
    );
  }

  _adminClient = createClient<Database>(supabaseUrl, serviceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
  return _adminClient;
}

export type TestSupabaseAdmin = ReturnType<typeof createTestSupabaseAdmin>;
