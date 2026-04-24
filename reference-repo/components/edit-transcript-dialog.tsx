"use client";

import { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ErrorLogger } from "@/lib/errorLogger";
import { getDisplayTranscript } from "@/lib/fixTranscriptCapitalization";

interface EditTranscriptDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentTranscript: string | null;
  transcriptManuallyEdited?: boolean;
  onSave: (transcript: string) => Promise<void>;
}

export function EditTranscriptDialog({
  open,
  onOpenChange,
  currentTranscript,
  transcriptManuallyEdited = false,
  onSave,
}: EditTranscriptDialogProps) {
  const [baseline, setBaseline] = useState("");
  const [transcript, setTranscript] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const prevOpen = useRef(false);

  // Reset transcript when dialog opens — use display version as baseline
  useEffect(() => {
    if (open && !prevOpen.current) {
      const initial = getDisplayTranscript(
        currentTranscript,
        transcriptManuallyEdited,
      );
      setBaseline(initial);
      setTranscript(initial);
    }
    prevOpen.current = open;
  }, [open, currentTranscript, transcriptManuallyEdited]);

  const isDirty = transcript.trim() !== baseline.trim();
  const isValid = transcript.trim().length > 0;

  const handleSave = async () => {
    if (!isValid || !isDirty) return;

    setIsLoading(true);
    try {
      await onSave(transcript.trim());
      toast.success("Transcript updated successfully");
      onOpenChange(false);
    } catch (error) {
      ErrorLogger.logError(error, {
        component: "EditTranscriptDialog",
        action: "save-transcript",
        feature: "clips",
      });
      toast.error(
        error instanceof Error ? error.message : "Failed to update transcript",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setTranscript(baseline);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-[700px]"
        onClick={(e) => e.stopPropagation()}
      >
        <DialogHeader>
          <DialogTitle>Edit Transcript</DialogTitle>
          <DialogDescription>
            Update the transcript for this clip. This will be displayed on the
            clip detail page.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="transcript">Transcript</Label>
            <Textarea
              id="transcript"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Enter the full transcript..."
              className="min-h-[300px] resize-none font-mono text-sm"
              disabled={isLoading}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={!isValid || !isDirty || isLoading}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
