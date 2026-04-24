import { Alert, AlertDescription } from "@/components/ui/alert";
import { ArrowLeft, AlertCircle } from "lucide-react";
import Link from "next/link";
import { checkInvitePermissions } from "./actions";
import { InviteFormClient } from "./components/InviteFormClient";

interface InviteTeamMemberPageProps {
  params: Promise<{ teamId: string }>;
}

export default async function InviteTeamMemberPage({ params }: InviteTeamMemberPageProps) {
  const { teamId } = await params;
  const { canInvite } = await checkInvitePermissions(teamId);

  if (!canInvite) {
    return (
      <div className="space-y-6">
        <div>
          <Link
            href={`/dashboard/teams/${teamId}/members`}
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Team Members
          </Link>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            You don&apos;t have permission to invite team members. Only team owners and administrators can send invitations.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/dashboard/teams/${teamId}/members`}
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Team Members
        </Link>
        <h1 className="text-3xl font-bold">Invite Team Member</h1>
        <p className="text-muted-foreground mt-2">
          Send an invitation to add new members to your team
        </p>
      </div>

      <InviteFormClient teamId={teamId} />
    </div>
  );
}