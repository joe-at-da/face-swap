"use client";

import { useState, useEffect, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AlertTriangle,
  Trash2,
  Loader2,
  Shield,
  AlertCircle,
  Users,
  Video
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { deleteTeamAction } from "../actions";
import { useTeamActions, teamStore } from "@/stores/teamStore";

interface TeamInfo {
  id: string;
  name: string;
  memberCount: number;
  clipCount: number;
}

interface DeleteTeamSectionProps {
  teamInfo: TeamInfo;
}

export function DeleteTeamSection({ teamInfo }: DeleteTeamSectionProps) {
  const router = useRouter();
  const teamActions = useTeamActions();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [confirmationText, setConfirmationText] = useState("");
  const [isPending, startTransition] = useTransition();

  const isConfirmationValid = confirmationText === teamInfo.name;

  // Reset confirmation text when dialog closes
  useEffect(() => {
    if (!isDialogOpen) {
      setConfirmationText("");
    }
  }, [isDialogOpen]);

  const handleDeleteTeam = async () => {
    if (!isConfirmationValid) {
      toast.error("Please type the team name exactly as shown");
      return;
    }

    startTransition(async () => {
      try {
        // Call the server action to delete the team (handles backend deletion)
        const result = await deleteTeamAction(teamInfo.id, confirmationText);

        if (!result.success) {
          throw new Error(result.error || "Failed to delete team");
        }

        // Update client-side state immediately to reflect the deletion
        // 1. Remove the team from the userTeams list using the store directly
        const teams = teamStore.userTeams.get();
        teamStore.userTeams.set(teams.filter((t) => t.id !== teamInfo.id));

        // 2. Switch to personal mode if this was the current team
        if (teamStore.currentTeamId.get() === teamInfo.id) {
          teamActions.switchToPersonal();
        }

        toast.success("Team deleted successfully");

        // Navigate to personal dashboard
        router.push("/dashboard");
        router.refresh();
      } catch (error) {
        console.error("Error deleting team:", error);
        toast.error(error instanceof Error ? error.message : "Failed to delete team");
      }
    });
  };

  return (
    <Card className="border-destructive/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-5 w-5" />
          Danger Zone
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Delete Team</h4>
          <p className="text-sm text-muted-foreground">
            Permanently delete this team, remove all members, and delete all team clips including video files. This action cannot be undone.
          </p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive" className="w-full">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Team
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Delete Team: {teamInfo.name}
              </DialogTitle>
              <DialogDescription>
                This action is permanent and cannot be undone. All team data will be deleted.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-3">
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-destructive mb-2">
                    <Shield className="h-4 w-4" />
                    <span className="text-sm font-medium">What will happen:</span>
                  </div>
                  <ul className="text-sm space-y-1.5 ml-6">
                    <li className="flex items-center gap-2">
                      <Users className="h-3 w-3" />
                      All {teamInfo.memberCount} team member{teamInfo.memberCount !== 1 ? "s" : ""} will be removed
                    </li>
                    <li className="flex items-center gap-2">
                      <Video className="h-3 w-3" />
                      All {teamInfo.clipCount} team clip{teamInfo.clipCount !== 1 ? "s" : ""} will be permanently deleted
                    </li>
                    <li>• All video files will be deleted from storage</li>
                    <li>• Team members will receive email notifications</li>
                    <li>• Members with no other teams will have their accounts removed</li>
                  </ul>
                </div>

                <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
                  <div className="font-medium mb-1">Team Summary:</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>Team: {teamInfo.name}</div>
                    <div>Members: {teamInfo.memberCount}</div>
                    <div>Clips: {teamInfo.clipCount}</div>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmation" className="text-destructive">
                  Type <code className="bg-muted px-1 rounded">{teamInfo.name}</code> to confirm:
                </Label>
                <Input
                  id="confirmation"
                  value={confirmationText}
                  onChange={(e) => setConfirmationText(e.target.value)}
                  placeholder="Type team name here..."
                  disabled={isPending}
                  autoComplete="off"
                />
                {confirmationText && !isConfirmationValid && (
                  <div className="flex items-center gap-1 text-xs text-destructive">
                    <AlertCircle className="h-3 w-3" />
                    <span>Team name does not match</span>
                  </div>
                )}
              </div>
            </div>

            <DialogFooter className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setIsDialogOpen(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteTeam}
                disabled={!isConfirmationValid || isPending}
                className="flex items-center gap-2"
              >
                {isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                {isPending ? "Deleting..." : "Delete Team"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
