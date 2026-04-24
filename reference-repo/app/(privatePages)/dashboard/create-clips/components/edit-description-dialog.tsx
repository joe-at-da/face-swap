"use client";

import { useState, useEffect } from "react";
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
import { updateClipDescription } from "@/app/actions/clip-descriptions";

interface EditDescriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clipId: string;
  currentDescription: string;
  onDescriptionUpdated: (newDescription: string) => void;
}

export function EditDescriptionDialog({
  open,
  onOpenChange,
  clipId,
  currentDescription,
  onDescriptionUpdated,
}: EditDescriptionDialogProps) {
  const [description, setDescription] = useState(currentDescription);
  const [isLoading, setIsLoading] = useState(false);

  // Reset description when dialog opens
  useEffect(() => {
    if (open) {
      setDescription(currentDescription);
    }
  }, [open, currentDescription]);

  const maxLength = 500;
  const charCount = description.length;
  const isValid = charCount > 0 && charCount <= maxLength;

  const handleSave = async () => {
    if (!isValid) return;

    setIsLoading(true);
    try {
      const result = await updateClipDescription(clipId, description.trim());

      if (!result.success) {
        throw new Error(result.error || "Failed to update description");
      }

      toast.success("Description updated successfully");
      if (result.description) {
        onDescriptionUpdated(result.description);
      }
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to update description:", error);
      toast.error(
        error instanceof Error ? error.message : "Failed to update description"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setDescription(currentDescription);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        className="sm:max-w-[600px]"
        onClick={(e) => e.stopPropagation()}
      >
        <DialogHeader>
          <DialogTitle>Edit Description</DialogTitle>
          <DialogDescription>
            Update the description for this clip. This will be displayed on the
            clip card and used for search.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter a concise description of what the MP discusses..."
              className="min-h-[120px] resize-none"
              maxLength={maxLength}
              disabled={isLoading}
            />
            <div className="flex justify-between text-sm">
              <p className="text-muted-foreground">
                Keep it concise and descriptive
              </p>
              <p
                className={`${
                  charCount > maxLength
                    ? "text-destructive"
                    : "text-muted-foreground"
                }`}
              >
                {charCount}/{maxLength}
              </p>
            </div>
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
            disabled={!isValid || isLoading}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
