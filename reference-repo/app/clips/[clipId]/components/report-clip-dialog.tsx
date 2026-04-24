"use client";

import { useTransition } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertTriangle,
  CircleHelp,
  Copyright,
  Loader2,
  ShieldAlert,
  Video,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form";
import { toast } from "sonner";
import { submitPublicClipReport } from "@/app/clips/[clipId]/actions";
import {
  publicClipReportFormSchema,
  type PublicClipReportFormValues,
  type PublicClipReportReason,
} from "@/schemas/publicClipReportSchema";

const REPORT_REASON_OPTIONS: Array<{
  value: PublicClipReportReason;
  label: string;
  icon: typeof Video;
}> = [
  { value: "wrong_clip", label: "Wrong clip or speaker", icon: Video },
  { value: "misleading", label: "Misleading or inaccurate", icon: AlertTriangle },
  { value: "copyright_or_privacy", label: "Copyright or privacy concern", icon: Copyright },
  { value: "harmful_or_abusive", label: "Harmful or abusive content", icon: ShieldAlert },
  { value: "other", label: "Other", icon: CircleHelp },
];

interface ReportClipDialogProps {
  clipId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ReportClipDialog({
  clipId,
  open,
  onOpenChange,
}: ReportClipDialogProps) {
  const [isPending, startTransition] = useTransition();
  const form = useForm<PublicClipReportFormValues>({
    resolver: zodResolver(publicClipReportFormSchema),
    defaultValues: { reason: undefined, details: "" },
  });

  const reason = form.watch("reason");
  const details = form.watch("details") ?? "";
  const detailsCount = details.trim().length;

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      form.reset();
    }
    onOpenChange(nextOpen);
  }

  function handleSubmit(values: PublicClipReportFormValues) {
    startTransition(async () => {
      const result = await submitPublicClipReport({
        clipId,
        reason: values.reason,
        details: values.details,
      });

      if (result.ok) {
        toast.success("This clip has been reported for review.");
        handleOpenChange(false);
        return;
      }

      switch (result.code) {
        case "validation_error":
          if (result.fieldErrors?.reason?.[0]) {
            form.setError("reason", { message: result.fieldErrors.reason[0] });
          }
          if (result.fieldErrors?.details?.[0]) {
            form.setError("details", { message: result.fieldErrors.details[0] });
          }
          return;
        case "duplicate_report":
          toast.info("You already reported this clip for that reason.");
          return;
        case "rate_limited":
          toast.error("Too many reports were submitted. Please try again later.");
          return;
        case "clip_unavailable":
          toast.error("This clip is no longer available.");
          return;
        case "persistence_error":
        default:
          toast.error("We could not save your report. Please try again.");
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Report This Clip</DialogTitle>
          <DialogDescription>
            Select a reason and we&apos;ll review it manually.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-2">
            <FormField
              control={form.control}
              name="reason"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <RadioGroup
                      value={field.value || undefined}
                      onValueChange={field.onChange}
                      className="space-y-2"
                    >
                      {REPORT_REASON_OPTIONS.map((option) => {
                        const Icon = option.icon;
                        const isSelected = field.value === option.value;

                        return (
                          <div
                            key={option.value}
                            className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                              isSelected
                                ? "border-primary bg-primary/5"
                                : "border-border hover:border-muted-foreground/50"
                            }`}
                          >
                            <RadioGroupItem
                              id={`report-reason-${option.value}`}
                              value={option.value}
                            />
                            <Icon
                              className={`h-4 w-4 shrink-0 ${
                                isSelected
                                  ? "text-primary"
                                  : "text-muted-foreground"
                              }`}
                            />
                            <Label
                              htmlFor={`report-reason-${option.value}`}
                              className="cursor-pointer text-sm font-medium"
                            >
                              {option.label}
                            </Label>
                          </div>
                        );
                      })}
                    </RadioGroup>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="details"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between gap-3">
                    <Label htmlFor="report-details" className="text-sm">
                      Additional details{" "}
                      <span className="font-normal text-muted-foreground">
                        (optional)
                      </span>
                    </Label>
                    <span className="text-xs text-muted-foreground">
                      {detailsCount}/2000
                    </span>
                  </div>
                  <FormControl>
                    <Textarea
                      id="report-details"
                      {...field}
                      placeholder="Anything that would help an admin review this clip."
                      maxLength={2000}
                      rows={3}
                      disabled={isPending}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={!reason || isPending}>
                {isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  "Submit report"
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
