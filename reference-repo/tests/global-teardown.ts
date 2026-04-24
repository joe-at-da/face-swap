import { createTestSupabaseAdmin } from "./e2e/helpers/supabase-admin";
import { cleanupAllTestData } from "./e2e/helpers/cleanup";

async function globalTeardown() {
  // Safety: refuse to run against non-local Supabase
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
  if (!supabaseUrl.includes("localhost") && !supabaseUrl.includes("127.0.0.1")) {
    throw new Error(
      `[Global Teardown] SUPABASE_URL does not point to localhost: ${supabaseUrl}\n` +
      "Refusing to run teardown against a non-local Supabase instance."
    );
  }

  console.log("[Global Teardown] Cleaning up all test data...");

  const admin = createTestSupabaseAdmin();
  await cleanupAllTestData(admin);

  console.log("[Global Teardown] Complete.");
}

export default globalTeardown;
