import "server-only";

import { createClient } from "@supabase/supabase-js";
import { Database } from "@/supabaseTypes";

export const supabaseAdminClient = createClient<Database>(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  },
);
