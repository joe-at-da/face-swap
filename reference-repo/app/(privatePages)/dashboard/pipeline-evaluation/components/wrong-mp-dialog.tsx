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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { ERROR_REASONS, type ErrorReason } from "../constants";

interface WrongMpDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (reason: ErrorReason) => void;
  isSubmitting: boolean;
}

export function WrongMpDialog({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
}: WrongMpDialogProps) {
  const [selectedReason, setSelectedReason] = useState<ErrorReason | null>(
    null
  );

  // Reset selection when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedReason(null);
    }
  }, [open]);

  // Keyboard shortcuts when dialog is open
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger if submitting
      if (isSubmitting) return;

      switch (event.key) {
        case "1":
          event.preventDefault();
          setSelectedReason("wrong_speaker_detected");
          break;
        case "2":
          event.preventDefault();
          setSelectedReason("wrong_mp_matched");
          break;
        case "Enter":
          event.preventDefault();
          if (selectedReason) {
            onSubmit(selectedReason);
          }
          break;
        case "Escape":
          event.preventDefault();
          onOpenChange(false);
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, selectedReason, isSubmitting, onSubmit, onOpenChange]);

  const handleSubmit = () => {
    if (selectedReason) {
      onSubmit(selectedReason);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>What went wrong?</DialogTitle>
          <DialogDescription>
            Select the reason why the MP identification is incorrect.
          </DialogDescription>
        </DialogHeader>

        <RadioGroup
          value={selectedReason ?? undefined}
          onValueChange={(value) => setSelectedReason(value as ErrorReason)}
          className="space-y-4 py-4"
        >
          {(Object.entries(ERROR_REASONS) as [ErrorReason, typeof ERROR_REASONS[ErrorReason]][]).map(
            ([key, reason], index) => (
              <div
                key={key}
                className={`flex items-start space-x-3 p-3 rounded-lg border transition-colors ${
                  selectedReason === key
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-muted-foreground/50"
                }`}
              >
                <RadioGroupItem value={key} id={key} className="mt-1" />
                <div className="flex-1">
                  <Label
                    htmlFor={key}
                    className="text-sm font-medium cursor-pointer flex items-center gap-2"
                  >
                    <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                      {index + 1}
                    </span>
                    {reason.label}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-1">
                    {reason.description}
                  </p>
                </div>
              </div>
            )
          )}
        </RadioGroup>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!selectedReason || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              "Submit"
            )}
          </Button>
        </DialogFooter>

        <p className="text-xs text-muted-foreground text-center">
          Press <kbd className="px-1 bg-muted rounded">1</kbd> or{" "}
          <kbd className="px-1 bg-muted rounded">2</kbd> to select,{" "}
          <kbd className="px-1 bg-muted rounded">Enter</kbd> to submit
        </p>
      </DialogContent>
    </Dialog>
  );
}
