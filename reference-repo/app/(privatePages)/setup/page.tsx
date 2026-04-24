import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { redirect } from "next/navigation";
import { SetupWizard } from "./components/setup-wizard";
import { Logo } from "@/components/logo";
import type { Database } from "@/supabaseTypes";

type MP = {
  member_id: number;
  display_name: string;
  party_abbreviation: string;
  party_name?: string;
  constituency_name: string;
  parliament_member_portraits: Array<{
    image_url: string;
    is_primary: boolean;
  }>;
};

export default async function SetupPage() {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // FIRST: If setup is already complete, redirect to dashboard
  // This prevents completed users from entering setup flows
  // Check explicitly for false (not undefined or true) to avoid redirect loops
  if (user.user_metadata.is_first_login === false && user.user_metadata.is_first_login !== undefined) {
    redirect("/dashboard");
  }

  // SECOND: Redirect parliament members to mp-setup
  if (user.email?.endsWith("@parliament.gov.uk")) {
    redirect("/mp-setup");
  }

  // THIRD: Check if user is a team member and redirect to team-setup
  // Only check this for users who haven't completed setup
  const { data: teamMember, error: teamError } = await supabase
    .from("team_members")
    .select("team_id")
    .eq("user_id", user.id)
    .limit(1)
    .maybeSingle();

  // Only redirect if we successfully found a team member record
  // or if user metadata explicitly indicates they're a team member
  if (!teamError && (teamMember || user.user_metadata.is_team_member)) {
    redirect("/team-setup");
  }

  // Load existing user data for form pre-population
  const existingUserData = {
    firstName: user.user_metadata.first_name || "",
    lastName: user.user_metadata.last_name || "",
    profileImage: user.user_metadata.profile_image || null,
  };

  // Load existing MP selection if any
  let existingMpSelection = null;
  try {
    const { data: userRoleData } = await supabase
      .from("user_roles")
      .select("member_id")
      .eq("user_id", user.id)
      .single();

    type UserRole = Pick<Database["public"]["Tables"]["user_roles"]["Row"], "member_id">;
    const userRole = userRoleData as UserRole | null;

    if (userRole?.member_id) {
      existingMpSelection = { selectedMpId: userRole.member_id };
    }
  } catch (error) {
    console.log("No existing MP selection found:", error);
  }

  // Fetch all MPs using pagination to bypass 1000 limit
  let mps: MP[] = [];
  try {
    let allMps: MP[] = [];
    let page = 0;
    const pageSize = 1000; // Max per query
    let hasMore = true;

    while (hasMore) {
      const { data: mpsData, error } = await supabase
        .from("parliament_members")
        .select(
          `
          member_id,
          display_name,
          party_abbreviation,
          party_name,
          constituency_name,
          parliament_member_portraits!inner (
            image_url,
            is_primary
          )
        `
        )
        .eq("is_current_member", true)
        .eq("is_deleted", false)
        .eq("parliament_member_portraits.is_deleted", false)
        .eq("parliament_member_portraits.is_primary", true)
        .order("display_name")
        .range(page * pageSize, (page + 1) * pageSize - 1);

      if (error) {
        console.error(`Failed to fetch MPs page ${page}:`, error);
        break;
      }

      if (mpsData && mpsData.length > 0) {
        type MPData = {
          member_id: number;
          display_name: string | null;
          party_abbreviation: string | null;
          party_name: string | null;
          constituency_name: string | null;
          parliament_member_portraits: Array<{
            image_url: string;
            is_primary: boolean | null;
          }>;
        };
        const mpsTyped = mpsData as unknown as MPData[];
        const transformedMps = mpsTyped.map((mp) => ({
          member_id: mp.member_id,
          display_name: mp.display_name || "Unknown MP",
          party_abbreviation: mp.party_abbreviation || "Unknown",
          party_name: mp.party_name || "Unknown Party",
          constituency_name: mp.constituency_name || "Unknown Constituency",
          parliament_member_portraits: mp.parliament_member_portraits.map(
            (portrait) => ({
              ...portrait,
              is_primary: portrait.is_primary ?? false,
            })
          ),
        }));
        allMps = allMps.concat(transformedMps);
        hasMore = mpsData.length === pageSize; // If we got a full page, there might be more
        page++;
      } else {
        hasMore = false;
      }

      // Safety break to prevent infinite loops
      if (page > 10) {
        console.warn(
          "MP pagination reached safety limit of 10 pages (10,000 records)"
        );
        break;
      }
    }

    mps = allMps;
    console.log(`Loaded ${mps.length} MPs across ${page} pages`);
  } catch (error) {
    console.error("Failed to fetch MPs server-side:", error);
    // Continue with empty array - client will show appropriate message
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 md:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Logo />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-8">
        <div className="text-center space-y-2 mb-8">
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            Welcome to Parliament Connect
          </h2>
          <p className="text-muted-foreground text-lg">
            Let&apos;s set up your account to get started
          </p>
        </div>

        <SetupWizard
          initialMps={mps}
          initialUserData={existingUserData}
          initialMpSelection={existingMpSelection}
        />
      </main>
    </div>
  );
}
