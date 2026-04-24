"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { format } from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  CalendarIcon,
  Loader2,
  Clock,
  Send,
} from "lucide-react";
import {
  createSocialMediaPostAction,
  getNextAvailableSlotAction,
} from "@/app/actions/postizActions";
import {
  createTeamSocialMediaPostAction,
  getTeamOwnerNextAvailableSlotAction,
} from "@/app/actions/teamPostizActions";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// Platforms that prefer horizontal (16:9 landscape) video format
// All other platforms will use vertical (9:16) for mobile engagement
// YouTube is the only platform where horizontal clearly wins for regular videos
const HORIZONTAL_PLATFORMS = ['youtube'];

const shareFormSchema = z.object({
  message: z.string().min(1, "Message is required"),
  postType: z.enum(["now", "schedule"]),
  scheduleDate: z.date().optional(),
  scheduleTime: z.string().optional(),
});

type ShareFormValues = z.infer<typeof shareFormSchema>;

interface ShareDialogProps {
  platform: {
    name: string;
    identifier: string;
    integrationId: string;
    icon: React.ComponentType<{ className?: string }>;
  };
  clipData: {
    clipUrl: string | null;
    verticalClipUrl: string | null;
    mpName: string;
    clipId: string;
    description?: string | null;
  };
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  teamId?: string | null;
  teamOwnerName?: string | null;
}

export function ShareDialog({
  platform,
  clipData,
  open,
  onOpenChange,
  onSuccess,
  teamId,
  teamOwnerName,
}: ShareDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const Icon = platform.icon;

  const form = useForm<ShareFormValues>({
    resolver: zodResolver(shareFormSchema),
    defaultValues: {
      message: clipData.description || `Check out this clip from ${clipData.mpName}!`,
      postType: "now",
      scheduleDate: undefined,
      scheduleTime: "",
    },
  });

  const postType = form.watch("postType");
  const isBluesky = platform.identifier === "bluesky";

  // Reset to "now" if Bluesky is selected (Bluesky doesn't support scheduled posts)
  useEffect(() => {
    if (isBluesky && postType === "schedule") {
      form.setValue("postType", "now");
    }
  }, [isBluesky, postType, form]);

  // Fetch and populate next available slot when user selects "Schedule"
  useEffect(() => {
    const fetchNextSlot = async () => {
      if (postType === "schedule" && !form.getValues("scheduleDate")) {
        // Use team or personal action based on teamId
        const response = teamId
          ? await getTeamOwnerNextAvailableSlotAction(teamId, platform.integrationId)
          : await getNextAvailableSlotAction(platform.integrationId);

        if (response.data) {
          const slotDate = new Date(response.data);
          form.setValue("scheduleDate", slotDate);

          const hours = String(slotDate.getHours()).padStart(2, "0");
          const minutes = String(slotDate.getMinutes()).padStart(2, "0");
          form.setValue("scheduleTime", `${hours}:${minutes}`);
        } else if (response.error) {
          console.error("Error fetching next slot:", response.error);
          // Fallback: set to tomorrow at 9 AM if API fails
          const tomorrow = new Date();
          tomorrow.setDate(tomorrow.getDate() + 1);
          tomorrow.setHours(9, 0, 0, 0);
          form.setValue("scheduleDate", tomorrow);
          form.setValue("scheduleTime", "09:00");
        }
      }
    };

    fetchNextSlot();
  }, [postType, platform.integrationId, teamId, form]);

  const onSubmit = async (values: ShareFormValues) => {
    setIsSubmitting(true);

    try {
      // For Facebook: Check if page selection is needed (inBetweenSteps=true)
      if (platform.identifier === "facebook") {
        const integrationCheck = await fetch(
          `/api/oauth/facebook/integration?integrationId=${platform.integrationId}`
        );
        const integrationData = await integrationCheck.json();

        // If inBetweenSteps=true, user hasn't selected a page yet
        if (integrationData.inBetweenSteps === true ||
            (integrationData.pages && integrationData.pages.length > 0)) {
          toast.error(
            "Please select a Facebook page first. Go to your profile settings to complete setup.",
            { duration: 6000 }
          );
          setIsSubmitting(false);
          return;
        }
      }

      // For YouTube: Check if channel selection is needed (inBetweenSteps=true)
      if (platform.identifier === "youtube") {
        const integrationCheck = await fetch(
          `/api/oauth/youtube/integration?integrationId=${platform.integrationId}`
        );
        const integrationData = await integrationCheck.json();

        // If inBetweenSteps=true, user hasn't selected a channel yet
        if (integrationData.inBetweenSteps === true ||
            (integrationData.channels && integrationData.channels.length > 0)) {
          toast.error(
            "Please select a YouTube channel first. Go to your profile settings to complete setup.",
            { duration: 6000 }
          );
          setIsSubmitting(false);
          return;
        }
      }

      // Prepare media URLs based on platform preference
      const mediaUrls: string[] = [];

      if (HORIZONTAL_PLATFORMS.includes(platform.identifier)) {
        // Horizontal platforms (YouTube): prefer horizontal, fallback to vertical
        if (clipData.clipUrl) {
          mediaUrls.push(clipData.clipUrl);
        } else if (clipData.verticalClipUrl) {
          mediaUrls.push(clipData.verticalClipUrl);
        }
      } else {
        // Vertical platforms (Twitter/X, TikTok, Instagram, LinkedIn, Facebook, etc.): prefer vertical, fallback to horizontal
        // Mobile-first strategy: vertical videos get 2.5x-4x more engagement on mobile platforms
        if (clipData.verticalClipUrl) {
          mediaUrls.push(clipData.verticalClipUrl);
        } else if (clipData.clipUrl) {
          mediaUrls.push(clipData.clipUrl);
        }
      }

      // Prepare schedule time if needed
      let scheduleTime: string | null = null;
      if (values.postType === "schedule" && values.scheduleDate) {
        const time = values.scheduleTime || "12:00";
        const [hours, minutes] = time.split(":");
        const scheduledDate = new Date(values.scheduleDate);
        scheduledDate.setHours(parseInt(hours), parseInt(minutes), 0, 0);
        scheduleTime = scheduledDate.toISOString();
      }

      // Create post - Postiz will download video from our URL and upload to platform
      // Use team or personal action based on teamId
      const response = teamId
        ? await createTeamSocialMediaPostAction(
            clipData.clipId, // User clip ID
            teamId,
            [platform.integrationId],
            [platform.identifier],
            values.message,
            mediaUrls,
            scheduleTime
          )
        : await createSocialMediaPostAction(
            clipData.clipId, // User clip ID
            [platform.integrationId],
            [platform.identifier],
            values.message,
            mediaUrls,
            scheduleTime
          );

      if (response.error) {
        toast.error(response.error);
        return;
      }

      toast.success(
        scheduleTime
          ? `Post scheduled for ${format(new Date(scheduleTime), "PPp")}`
          : "Post published successfully!"
      );

      onSuccess();
      onOpenChange(false);
      form.reset();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to create post"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Icon className="h-5 w-5" />
            Share to {platform.name}
          </DialogTitle>
          <DialogDescription>
            {teamId && teamOwnerName ? (
              <>
                Posting as team using <span className="font-semibold">{teamOwnerName}&apos;s</span> {platform.name} account
              </>
            ) : (
              <>Create a post with this clip to share on {platform.name}</>
            )}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Message Field */}
            <FormField
              control={form.control}
              name="message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Message</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Write your post message..."
                      className="min-h-[120px]"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Post Type */}
            <FormField
              control={form.control}
              name="postType"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>When to post</FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                      className="flex gap-4"
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="now" id="now" />
                        <Label htmlFor="now" className="cursor-pointer">
                          Post Now
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem
                          value="schedule"
                          id="schedule"
                          disabled={isBluesky}
                        />
                        <Label
                          htmlFor="schedule"
                          className={cn(
                            "cursor-pointer",
                            isBluesky && "text-muted-foreground cursor-not-allowed"
                          )}
                        >
                          Schedule
                          {isBluesky && (
                            <span className="ml-1 text-xs">(not supported)</span>
                          )}
                        </Label>
                      </div>
                    </RadioGroup>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Schedule Date & Time */}
            {postType === "schedule" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="scheduleDate"
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>Date</FormLabel>
                      <Popover>
                        <PopoverTrigger asChild>
                          <FormControl>
                            <Button
                              variant="outline"
                              className={cn(
                                "pl-3 text-left font-normal",
                                !field.value && "text-muted-foreground"
                              )}
                            >
                              {field.value ? (
                                format(field.value, "PPP")
                              ) : (
                                <span>Pick a date</span>
                              )}
                              <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                            </Button>
                          </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                          <Calendar
                            mode="single"
                            selected={field.value}
                            onSelect={field.onChange}
                            disabled={(date) =>
                              date < new Date(new Date().setHours(0, 0, 0, 0))
                            }
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="scheduleTime"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Time</FormLabel>
                      <FormControl>
                        <Input type="time" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {postType === "schedule" ? "Scheduling..." : "Posting..."}
                  </>
                ) : postType === "schedule" ? (
                  <>
                    <Clock className="h-4 w-4 mr-2" />
                    Schedule Post
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Post Now
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
