import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { Header } from "./header";

export async function AuthNavHeader() {
  const supabase = await createSupabaseServerClient();

  const { data: { user } } = await supabase.auth.getUser();

  return <Header isAuthenticated={!!user} user={user} />;
}