import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { redirect } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Users, Mail, AlertCircle, Home } from "lucide-react";
import Link from "next/link";
import { signOut } from "@/app/actions/auth";

export default async function NoTeamAccessPage() {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // Check if user actually has team access - if they do, redirect to dashboard
  const { data: teamMember } = await supabase
    .from("team_members")
    .select("team_id")
    .eq("user_id", user.id)
    .limit(1)
    .maybeSingle();

  if (teamMember) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-2xl space-y-8">
        <Card className="p-8 md:p-12">
          <div className="space-y-6">
            {/* Icon and Header */}
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <div className="rounded-full bg-muted p-4">
                  <Users className="h-12 w-12 text-muted-foreground" />
                </div>
              </div>

              <div className="space-y-2">
                <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
                  No Team Access
                </h1>
                <p className="text-lg text-muted-foreground">
                  You are not currently a member of any team
                </p>
              </div>
            </div>

            {/* Information Alert */}
            <Alert className="border-muted">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">
                This could happen if:
                <ul className="mt-2 space-y-1 list-disc list-inside">
                  <li>You were removed from a team by an administrator</li>
                  <li>You left a team voluntarily</li>
                  <li>Your team invitation expired</li>
                </ul>
              </AlertDescription>
            </Alert>

            {/* What You Can Do Section */}
            <div className="space-y-4 pt-4">
              <h2 className="text-xl font-semibold text-foreground">
                What you can do
              </h2>

              <div className="space-y-3">
                <div className="flex items-start gap-3 p-4 rounded-lg border border-border bg-card">
                  <Mail className="h-5 w-5 text-primary mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-medium text-foreground">
                      Contact Your Team Administrator
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      If you believe this is a mistake, reach out to your team administrator to request access.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 rounded-lg border border-border bg-card">
                  <Users className="h-5 w-5 text-primary mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-medium text-foreground">
                      Request a New Invitation
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Ask your team owner to send you a new team invitation email.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Button asChild className="flex-1" size="lg">
                <Link href="/">
                  <Home className="mr-2 h-4 w-4" />
                  Return to Home
                </Link>
              </Button>
              <form action={signOut} className="flex-1">
                <Button type="submit" variant="outline" className="w-full" size="lg">
                  Sign Out
                </Button>
              </form>
            </div>

            {/* Support Contact */}
            <div className="text-center pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                Need help?{" "}
                <a
                  href="mailto:support@mpai.com"
                  className="text-primary hover:underline"
                >
                  Contact support
                </a>
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
