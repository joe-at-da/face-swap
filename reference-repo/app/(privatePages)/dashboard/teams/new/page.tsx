import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { redirect } from "next/navigation";
import { CreateTeamForm } from "./components/create-team-form";
import { isActualMPCached } from "@/lib/user-helpers";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default async function CreateTeamPage() {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // Check if user can create teams (only actual MPs can)
  const userCanCreateTeam = await isActualMPCached(user.id, user.email!, supabaseAdminClient);

  // If user cannot create teams, show contact message
  if (!userCanCreateTeam) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle>Contact us to create a team</CardTitle>
              <CardDescription>
                Team creation is currently limited to Parliament Members and authorized users.
                If you need to create a team, please contact us.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href="/contact">Contact Us</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // User can create teams, proceed to form
  return <CreateTeamForm />;
}