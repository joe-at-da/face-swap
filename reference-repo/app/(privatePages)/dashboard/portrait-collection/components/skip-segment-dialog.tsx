"use client";

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
import { Loader2, AlertCircle } from "lucide-react";
import { useState } from "react";
import { SKIP_REASONS, type SkipReason } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface SkipSegmentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isSubmitting: boolean;
  onConfirm: (skipReason: SkipReason) => void;
}

export function SkipSegmentDialog({
  open,
  onOpenChange,
  isSubmitting,
  onConfirm,
}: SkipSegmentDialogProps) {
  const [selectedReason, setSelectedReason] = useState<SkipReason | null>(null);

  const handleConfirm = () => {
    if (selectedReason) {
      onConfirm(selectedReason);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!isSubmitting) {
      setSelectedReason(null); // Reset when closing
      onOpenChange(newOpen);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Skip This Segment</DialogTitle>
          <DialogDescription>
            Why are you skipping this segment? This helps improve our data quality.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <RadioGroup
            value={selectedReason || ""}
            onValueChange={(value) => setSelectedReason(value as SkipReason)}
            disabled={isSubmitting}
          >
            {Object.entries(SKIP_REASONS).map(([key, reason]) => (
              <div key={key} className="flex items-start space-x-3 space-y-0">
                <RadioGroupItem value={key} id={key} className="mt-1" />
                <div className="flex-1 space-y-1">
                  <Label
                    htmlFor={key}
                    className="cursor-pointer font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    {reason.label}
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    {reason.description}
                  </p>
                </div>
              </div>
            ))}
          </RadioGroup>

          {/* Info Message */}
          <div className="flex items-start gap-3 rounded-lg border border-orange-500/20 bg-orange-500/10 p-3">
            <AlertCircle className="h-5 w-5 flex-shrink-0 text-orange-600 dark:text-orange-400" />
            <p className="text-sm text-foreground">
              Skipped segments will be marked as evaluated and won&apos;t appear in the queue again.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={!selectedReason || isSubmitting}
            variant="destructive"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Skipping...
              </>
            ) : (
              "Skip Segment"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
