import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UserPlus, ArrowLeft, Mail } from "lucide-react";
import Link from "next/link";
import { loadTeamMembers } from "./actions";
import { MembersPageClient } from "./components/MembersPageClient";
import { InvitationsList } from "./components/InvitationsList";

interface TeamMembersPageProps {
  params: Promise<{ teamId: string }>;
}

export default async function TeamMembersPage({ params }: TeamMembersPageProps) {
  const { teamId } = await params;
  const data = await loadTeamMembers(teamId);

  const userCanManage = data.userRole === "owner" || data.userRole === "administrator";

  const pendingCount = data.invitations.filter(i => i.status === "pending").length;
  const expiredCount = data.invitations.length - pendingCount;
  const invitationSummary = [
    pendingCount > 0 && `${pendingCount} pending`,
    expiredCount > 0 && `${expiredCount} expired`,
  ].filter(Boolean).join(", ");

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/dashboard/teams/${teamId}`}
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Team Dashboard
        </Link>
        <h1 className="text-3xl font-bold">Team Members</h1>
        <p className="text-muted-foreground mt-2">
          Manage your team members and their roles
        </p>
      </div>

      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">
            {data.members.length} member{data.members.length !== 1 ? "s" : ""} in this team
          </p>
          {userCanManage && invitationSummary && (
            <p className="text-sm text-muted-foreground">
              {invitationSummary} invitation{data.invitations.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        {userCanManage && (
          <Button asChild>
            <Link href={`/dashboard/teams/${teamId}/invite`}>
              <UserPlus className="mr-2 h-4 w-4" />
              Invite Members
            </Link>
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>
            Team members can view and edit all team clips
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MembersPageClient
            members={data.members}
            userRole={data.userRole}
            teamId={teamId}
          />
        </CardContent>
      </Card>

      {/* Invitations */}
      {userCanManage && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Invitations
            </CardTitle>
            <CardDescription>
              Manage pending and expired team invitations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <InvitationsList invitations={data.invitations} teamId={teamId} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}