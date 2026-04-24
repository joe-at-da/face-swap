import { Badge } from "@/components/ui/badge";
import { Check } from "lucide-react";
import { SmartAvatar } from "@/components/smart-avatar";
import type { InvitationData } from "../types";

interface InvitationDetailsProps {
  invitation: InvitationData;
}

function getDisplayName(user: { first_name: string | null; last_name: string | null; email: string }) {
  if (user.first_name && user.last_name) return `${user.first_name} ${user.last_name}`;
  if (user.first_name) return user.first_name;
  return user.email;
}

function formatRole(role: string) {
  if (role === "owner") return "Team Owner";
  if (role === "administrator") return "Administrator";
  return "Team Member";
}

export function InvitationDetails({ invitation }: InvitationDetailsProps) {
  const ownerName = getDisplayName(invitation.team.owner);

  return (
    <>
      {/* Team Name & Owner */}
      <div className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-center text-foreground">
          {invitation.team.name}
        </h2>
        <div className="flex items-center justify-between w-full gap-3">
          <div className="flex items-center gap-3">
            <SmartAvatar
              email={invitation.team.owner.email}
              firstName={invitation.team.owner.first_name || undefined}
              lastName={invitation.team.owner.last_name || undefined}
              className="w-10 h-10"
            />
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-medium text-foreground truncate">{ownerName}</span>
              {ownerName !== invitation.team.owner.email && (
                <span className="text-xs text-muted-foreground truncate">
                  {invitation.team.owner.email}
                </span>
              )}
            </div>
          </div>
          <Badge variant="secondary">
            <span className="text-xs">Team Owner</span>
          </Badge>
        </div>
      </div>

      {/* Invitation Info Rows */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between py-2 border-b border-border">
          <span className="text-sm text-muted-foreground">Your Email</span>
          <span className="text-sm font-medium text-foreground truncate ml-2">{invitation.email}</span>
        </div>
        <div className="flex items-center justify-between py-2 border-b border-border">
          <span className="text-sm text-muted-foreground">Your Role</span>
          <span className="text-sm font-medium text-foreground">{formatRole(invitation.role)}</span>
        </div>
        <div className="flex items-center justify-between py-2 border-b border-border">
          <span className="text-sm text-muted-foreground">Expires</span>
          <span className="text-sm font-medium text-foreground">
            {new Date(invitation.expiresAt).toLocaleDateString("en-US", {
              month: "2-digit",
              day: "2-digit",
              year: "numeric",
            })}
          </span>
        </div>
      </div>

      {/* Benefits Card */}
      <div className="flex items-start gap-3 p-4 bg-primary/5 border border-primary/20 rounded-lg">
        <div className="rounded-lg bg-primary/10 flex items-center justify-center p-2 flex-shrink-0">
          <Check className="w-4 h-4 text-primary" />
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="text-sm font-medium text-foreground">
            By joining this team, you&apos;ll get access to:
          </p>
          <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
            <li>Create and edit video clips from parliament sessions</li>
            <li>Search parliament footage by topic and context</li>
            <li>Follow MPs and get notifications when they speak</li>
            <li>Share clips with team members</li>
          </ul>
        </div>
      </div>
    </>
  );
}
