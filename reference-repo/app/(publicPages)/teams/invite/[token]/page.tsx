import { InvitationContent } from "./components/invitation-content";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";

interface InvitePageProps {
  params: Promise<{
    token: string;
  }>;
  searchParams: Promise<{
    error?: string;
  }>;
}

export default async function InvitePage({ params, searchParams }: InvitePageProps) {
  const { token } = await params;
  const { error } = await searchParams;
  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();

  return (
    <InvitationContent
      token={token}
      currentUserEmail={user?.email ?? null}
      initialErrorCode={error ?? null}
    />
  );
}
