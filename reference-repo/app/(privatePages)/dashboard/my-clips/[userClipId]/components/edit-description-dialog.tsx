"use client";

import { useState } from "react";
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
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

interface EditDescriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clipId: string;
  currentDescription: string | null;
  onUpdate: (newDescription: string | null) => void;
}

export function EditDescriptionDialog({
  open,
  onOpenChange,
  clipId,
  currentDescription,
  onUpdate,
}: EditDescriptionDialogProps) {
  const [description, setDescription] = useState(currentDescription || "");
  const [isLoading, setIsLoading] = useState(false);

  const handleSave = async () => {
    if (description.trim() === (currentDescription || "")) {
      onOpenChange(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`/api/user-clips/${clipId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          description: description.trim() || null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to update description");
      }

      toast.success("Description updated successfully");
      onUpdate(description.trim() || null);
      onOpenChange(false);
    } catch (error) {
      console.error("Error updating description:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update description"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setDescription(currentDescription || "");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit Description</DialogTitle>
          <DialogDescription>
            Update the description for this clip. The embedding will be
            automatically regenerated.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter clip description..."
            disabled={isLoading}
            className="min-h-[120px]"
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

