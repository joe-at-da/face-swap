import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { redirect } from "next/navigation";
import { Toaster } from "@/components/ui/sonner";
import { AuthRedirectGuard } from "./components/auth-redirect-guard";

export const dynamic = "force-dynamic";

export default async function PrivatePagesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Redirect to home if not authenticated (server-side check)
  if (!user) {
    redirect("/");
  }

  return (
    <>
      {/* Client-side guard for cross-tab logout detection */}
      <AuthRedirectGuard>
        {children}
      </AuthRedirectGuard>
      <Toaster position="top-center" />
    </>
  );
}