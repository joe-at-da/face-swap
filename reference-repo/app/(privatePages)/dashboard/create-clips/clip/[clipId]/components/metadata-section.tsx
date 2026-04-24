"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Edit3, Copy, Loader2, CircleAlert } from "lucide-react";
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
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { markClipAsFalsePositive } from "@/app/(privatePages)/dashboard/create-clips/actions";
import { getErrorMessage } from "@/lib/getErrorMessage";
import type {
  ParliamentMemberClip,
  ParliamentMember,
} from "@/types/parliament";

interface MetadataSectionProps {
  clip: ParliamentMemberClip;
  mp: ParliamentMember;
  teamId?: string;
  actualDuration?: number | null;
}

export default function MetadataSection({ clip, teamId }: MetadataSectionProps) {
  const router = useRouter();

  // Export state
  const [isExporting, setIsExporting] = useState(false);

  // False positive state
  const [isMarkingAsFalsePositive, setIsMarkingAsFalsePositive] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const handleCreateCustomClip = () => {
    const url = `/dashboard/create-clips/edit-clip/${clip.id}${teamId ? `?teamId=${teamId}` : ''}`;
    router.push(url);
  };

  /**
   * Handle "Copy this into my clips" button - copies the clip as-is using v2 format.
   * The server constructs the v2 composition JSON and triggers RunPod rendering.
   */
  const handleCopyToMyClips = async () => {
    setIsExporting(true);

    try {
      const response = await fetch("/api/clips/copy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clipId: clip.id,
          teamId: teamId || undefined,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to copy clip");
      }

      toast.success("Clip copied successfully!", {
        description: "Your clip is being processed and will appear in My Clips",
        duration: 5000,
      });

      if (data.userClipId) {
        router.push(`/dashboard/my-clips/${data.userClipId}`);
      }
    } catch (error) {
      console.error("Copy error:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";
      toast.error("Copy failed", {
        description: errorMessage,
        duration: 5000,
      });
    } finally {
      setIsExporting(false);
    }
  };

  /**
   * Handle marking clip as false positive
   */
  const handleMarkAsFalsePositive = async () => {
    if (isMarkingAsFalsePositive) return;

    setIsMarkingAsFalsePositive(true);
    setShowConfirmDialog(false);

    try {
      const { error } = await markClipAsFalsePositive(clip.id, teamId);

      if (error) {
        throw new Error(error);
      }

      // Show success toast
      toast.success("Clip marked as false positive");

      // Redirect back to clips list
      router.push("/dashboard/create-clips");
    } catch (error: unknown) {
      const message = getErrorMessage(error);
      console.error("Error in handleMarkAsFalsePositive:", message);
      toast.error(message);
      setIsMarkingAsFalsePositive(false);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 pb-4 text-lg font-sans font-bold">

            Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            onClick={handleCreateCustomClip}
            className="w-full justify-center gap-2 min-h-[44px] text-base font-sans"
          >
            <Edit3 className="h-4 w-4" />
            Create Custom Clip
          </Button>

          <Button
            onClick={handleCopyToMyClips}
            disabled={isExporting}
            variant="outline"
            className="w-full justify-center gap-2 min-h-[44px] text-base font-sans"
          >
            {isExporting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Copying...
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                Copy this into my clips
              </>
            )}
          </Button>

          <Button
            onClick={() => setShowConfirmDialog(true)}
            disabled={isMarkingAsFalsePositive}
            variant="destructive"
            className="w-full justify-center gap-2 min-h-[44px] text-base font-sans"
          >
            {isMarkingAsFalsePositive ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Marking...
              </>
            ) : (
              <>
                <CircleAlert className="h-4 w-4" />
                Mark as incorrect
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Mark clip as incorrect?</AlertDialogTitle>
            <AlertDialogDescription>
              This will mark the clip as incorrect and remove it from the clips list.
              You will be redirected back to the clips page.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isMarkingAsFalsePositive}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleMarkAsFalsePositive}
              disabled={isMarkingAsFalsePositive}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isMarkingAsFalsePositive ? "Marking..." : "Mark as incorrect"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
