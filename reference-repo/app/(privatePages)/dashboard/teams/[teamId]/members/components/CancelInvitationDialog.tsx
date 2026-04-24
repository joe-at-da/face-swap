"use client";

import { useTransition } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { cancelInvitation } from "../actions";

interface CancelInvitationDialogProps {
  teamId: string;
  invitationId: string | null;
  email: string | null;
  onClose: () => void;
}

export function CancelInvitationDialog({
  teamId,
  invitationId,
  email,
  onClose,
}: CancelInvitationDialogProps) {
  const [isPending, startTransition] = useTransition();

  function handleCancel() {
    if (!invitationId || !email) return;

    startTransition(async () => {
      const result = await cancelInvitation(teamId, invitationId);
      if (result.success) {
        toast.success(`Invitation cancelled for ${email}`);
        onClose();
      } else {
        toast.error(result.error || "Failed to cancel invitation");
      }
    });
  }

  return (
    <AlertDialog open={!!invitationId} onOpenChange={onClose}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Cancel Invitation</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to cancel the invitation to{" "}
            <span className="font-medium">{email}</span>? They will no longer
            be able to join the team using this invitation link.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>Keep Invitation</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleCancel}
            disabled={isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isPending ? "Cancelling..." : "Cancel Invitation"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
