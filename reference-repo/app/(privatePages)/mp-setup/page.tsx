import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { redirect } from "next/navigation";
import { MpSetupDisplay } from "./components/mp-setup-display";
import { Logo } from "@/components/logo";
import { isActualMP } from "@/lib/user-helpers";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

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

export default async function MPSetupPage() {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // Redirect non-MP members to regular setup
  if (!(await isActualMP(user, supabaseAdminClient))) {
    redirect("/setup");
  }

  // If setup is already complete, redirect to dashboard
  if (user.user_metadata.is_first_login === false) {
    redirect("/dashboard");
  }

  // Load existing user data for form pre-population
  const existingUserData = {
    firstName: user.user_metadata.first_name || "",
    lastName: user.user_metadata.last_name || "",
    profileImage: user.user_metadata.profile_image || null,
  };

  // Find the MP's record by matching their email with parliament_member_contacts
  let mpRecord: MP | null = null;
  try {
    // First, find the MP contact record that matches the user's email
    const { data: contactData } = await supabase
      .from("parliament_member_contacts")
      .select(
        `
        member_id,
        parliament_members!inner (
          member_id,
          display_name,
          party_abbreviation,
          party_name,
          constituency_name,
          is_current_member,
          is_deleted,
          parliament_member_portraits!inner (
            image_url,
            is_primary
          )
        )
      `
      )
      .eq("email", user.email || "")
      .eq("is_deleted", false)
      .eq("parliament_members.is_current_member", true)
      .eq("parliament_members.is_deleted", false)
      .eq("parliament_members.parliament_member_portraits.is_deleted", false)
      .eq("parliament_members.parliament_member_portraits.is_primary", true)
      .limit(1);

    if (contactData && contactData.length > 0) {
      type ContactData = {
        member_id: number;
        parliament_members: {
          member_id: number;
          display_name: string | null;
          party_abbreviation: string | null;
          party_name: string | null;
          constituency_name: string | null;
          is_current_member: boolean | null;
          is_deleted: boolean | null;
          parliament_member_portraits: Array<{
            image_url: string;
            is_primary: boolean | null;
          }>;
        };
      };
      const contact = contactData[0] as unknown as ContactData;
      mpRecord = {
        member_id: contact.parliament_members.member_id,
        display_name: contact.parliament_members.display_name || "Unknown MP",
        party_abbreviation:
          contact.parliament_members.party_abbreviation || "Unknown",
        party_name: contact.parliament_members.party_name || "Unknown Party",
        constituency_name:
          contact.parliament_members.constituency_name ||
          "Unknown Constituency",
        parliament_member_portraits:
          contact.parliament_members.parliament_member_portraits.map(
            (portrait) => ({
              ...portrait,
              is_primary: portrait.is_primary ?? false,
            })
          ),
      };
    }
  } catch (error) {
    console.error("Failed to find MP record:", error);
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
            Let&apos;s set up your MP account
          </p>
        </div>

        <MpSetupDisplay userData={existingUserData} mpRecord={mpRecord} />
      </main>
    </div>
  );
}
