"use client";

import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Mail, Clock, AlertCircle, MoreVertical, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { PendingInvitation } from "@/types/teams";
import { resendInvitation } from "../actions";
import { CancelInvitationDialog } from "./CancelInvitationDialog";

interface InvitationsListProps {
  invitations: PendingInvitation[];
  teamId: string;
}

export function InvitationsList({ invitations, teamId }: InvitationsListProps) {
  const [isPending, startTransition] = useTransition();
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [cancellingInvitation, setCancellingInvitation] = useState<{
    id: string;
    email: string;
  } | null>(null);

  if (invitations.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No invitations have been sent yet
      </div>
    );
  }

  function handleResend(invitationId: string, email: string) {
    setProcessingId(invitationId);
    startTransition(async () => {
      const result = await resendInvitation(teamId, invitationId);
      if (result.success) {
        toast.success(`Invitation resent to ${email}`);
      } else {
        toast.error(result.error || "Failed to resend invitation");
      }
      setProcessingId(null);
    });
  }

  return (
    <div className="space-y-4">
      {invitations.map((invitation) => {
        const isExpired = invitation.status === "expired";
        const isProcessing = processingId === invitation.id;
        const daysRemaining = Math.ceil(
          (new Date(invitation.expiresAt).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
        );

        return (
          <div key={invitation.id} className="flex items-center justify-between py-3 border-b last:border-0">
            <div className="flex items-center gap-3">
              <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
                isExpired ? "bg-destructive/10" : "bg-muted"
              }`}>
                <Mail className={`h-5 w-5 ${isExpired ? "text-destructive" : "text-muted-foreground"}`} />
              </div>
              <div>
                <div className="font-medium">{invitation.email}</div>
                <div className="text-xs text-muted-foreground">
                  Invited by {invitation.invitedBy} • {new Date(invitation.invitedAt).toLocaleDateString()}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isExpired ? (
                <Badge variant="destructive" className="flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  Expired
                </Badge>
              ) : (
                <Badge variant="outline" className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {daysRemaining} day{daysRemaining !== 1 ? "s" : ""} left
                </Badge>
              )}
              <Badge variant={invitation.role === "administrator" ? "secondary" : "outline"}>
                {invitation.role === "administrator" ? "Administrator" : "Member"}
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" disabled={isProcessing || isPending}>
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={() => handleResend(invitation.id, invitation.email)}
                    disabled={isProcessing}
                  >
                    <Send className="mr-2 h-4 w-4" />
                    Resend Invitation
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => setCancellingInvitation({ id: invitation.id, email: invitation.email })}
                    className="text-destructive"
                    disabled={isProcessing}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Cancel Invitation
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        );
      })}

      <CancelInvitationDialog
        teamId={teamId}
        invitationId={cancellingInvitation?.id ?? null}
        email={cancellingInvitation?.email ?? null}
        onClose={() => setCancellingInvitation(null)}
      />
    </div>
  );
}
