"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
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
import { removeMember } from "../actions";

interface RemoveMemberDialogProps {
  teamId: string;
  userId: string | null;
  onClose: () => void;
}

export function RemoveMemberDialog({ teamId, userId, onClose }: RemoveMemberDialogProps) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  async function handleRemoveMember() {
    if (!userId) return;

    startTransition(async () => {
      const result = await removeMember(teamId, userId);

      if (result.success) {
        toast.success("Member removed from team");
        router.refresh();
        onClose();
      } else {
        toast.error(result.error || "Failed to remove member");
      }
    });
  }

  return (
    <AlertDialog open={!!userId} onOpenChange={onClose}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove Team Member</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to remove this member from the team? They will lose access to all team clips and resources.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleRemoveMember}
            disabled={isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isPending ? "Removing..." : "Remove Member"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}