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

interface EditTitleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clipId: string;
  currentTitle: string | null;
  onUpdate: (newTitle: string | null) => void;
}

export function EditTitleDialog({
  open,
  onOpenChange,
  clipId,
  currentTitle,
  onUpdate,
}: EditTitleDialogProps) {
  const [title, setTitle] = useState(currentTitle || "");
  const [isLoading, setIsLoading] = useState(false);

  const handleSave = async () => {
    if (title.trim() === (currentTitle || "")) {
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
          title: title.trim() || null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to update title");
      }

      toast.success("Title updated successfully");
      onUpdate(title.trim() || null);
      onOpenChange(false);
    } catch (error) {
      console.error("Error updating title:", error);
      toast.error(
        error instanceof Error ? error.message : "Failed to update title"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setTitle(currentTitle || "");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Title</DialogTitle>
          <DialogDescription>
            Update the title for this clip. The embedding will be automatically
            regenerated.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <Textarea
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter clip title..."
            disabled={isLoading}
            className="min-h-[60px] resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSave();
              }
            }}
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

