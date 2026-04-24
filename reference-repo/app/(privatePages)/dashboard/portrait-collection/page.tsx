import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { PortraitCollectionClient } from "@/app/(privatePages)/dashboard/portrait-collection/components/portrait-collection-client";
import { getPortraitCollectionStats } from "@/app/(privatePages)/dashboard/portrait-collection/lib/get-stats";
import type { PortraitCollectionStats } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

export const metadata = {
  title: "Portrait Collection | MP AI",
  description: "Identify MPs in unidentified segments to improve face recognition",
};

export default async function PortraitCollectionPage() {
  const supabase = await createSupabaseServerClient();

  // Check authentication
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    redirect("/login");
  }

  // Check if user has @veedoo.io or @veedoo.com email
  const email = user.email;
  if (
    !email ||
    (!email.endsWith("@veedoo.io") && !email.endsWith("@veedoo.com"))
  ) {
    redirect("/dashboard");
  }

  // Fetch initial stats directly (server-side)
  let initialStats: PortraitCollectionStats = {
    totalUnidentified: 0,
    evaluatedCount: 0,
    portraitsAddedCount: 0,
    remainingCount: 0,
    activeEvaluators: 0,
    completionPercentage: 0,
  };

  try {
    initialStats = await getPortraitCollectionStats();
  } catch (error) {
    console.error("Error fetching initial stats:", error);
  }

  return (
    <div className="container mx-auto max-w-5xl py-8">
      <div className="mb-8 space-y-2">
        <h1 className="text-3xl font-bold">Portrait Collection</h1>
        <p className="text-muted-foreground">
          Help improve MP identification by reviewing unidentified segments and
          collecting face images
        </p>
      </div>

      <PortraitCollectionClient initialStats={initialStats} userId={user.id} />
    </div>
  );
}
