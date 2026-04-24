"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";

import { Button } from "@/components/ui/button";
import {
  Clock,
  Calendar,
  Edit,
  MoreVerticalIcon,
  CircleAlert,
} from "lucide-react";
import { format } from "date-fns";
import { formatDuration } from "@/lib/formatDuration";
import PreviewVideo from "./preview-video";
import { EditDescriptionDialog } from "./edit-description-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type {
  ParliamentMemberClip,
  ParliamentMember,
} from "@/types/parliament";
import { markClipAsFalsePositive } from "../actions";
import { getErrorMessage } from "@/lib/getErrorMessage";
import { toast } from "sonner";
import { useCurrentTeam, useIsPersonalMode } from "@/stores/teamStore";
import { isMPEmail } from "@/lib/domains";
import { use$ } from "@legendapp/state/react";
import { userStore$ } from "@/stores/userStore";
import { getDisplayTranscript } from "@/lib/fixTranscriptCapitalization";

interface ClipCardProps {
  clip: ParliamentMemberClip;
  mp: ParliamentMember;
  teamId?: string;
  searchType?: "text" | "hybrid";
}

export default function ClipCard({ clip, teamId, searchType }: ClipCardProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentTeam = useCurrentTeam();
  const isPersonalMode = useIsPersonalMode();
  // Get email from session - use$ properly unwraps the observable
  const sessionEmail = use$(userStore$.session.user.email);
  // Track if client has mounted (to avoid hydration mismatch with Legend State stores)
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  // Handle empty strings as null - only use description if it has actual content
  const [description, setDescription] = useState(
    clip.description?.trim() || null
  );
  // Store actual video duration (from video file metadata)
  const [actualDuration, setActualDuration] = useState<number | null>(null);
  const [isMarkingAsFalsePositive, setIsMarkingAsFalsePositive] =
    useState<boolean>(false);
  const [isDeleted, setIsDeleted] = useState<boolean>(false);

  // Check if user can edit description
  // Only compute after hydration to avoid server/client mismatch (Legend State stores
  // read from localStorage on client but have default values on server)
  let canEditDescription = false;

  if (isMounted) {
    if (isPersonalMode) {
      const userEmail =
        typeof sessionEmail === "string" && sessionEmail ? sessionEmail : null;
      if (userEmail) {
        canEditDescription = isMPEmail(userEmail);
      }
    } else if (currentTeam) {
      canEditDescription =
        currentTeam.userRole === "owner" ||
        currentTeam.userRole === "administrator";
    }
  }

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return "Unknown date";
    try {
      return format(new Date(dateStr), "MMM d, yyyy");
    } catch {
      return "Unknown date";
    }
  };


  const truncateText = (text: string, maxLength: number): string => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + "...";
  };

  const handleClick = () => {
    // Don't navigate if the edit dialog is open
    if (isEditDialogOpen) {
      return;
    }

    // Preserve search params when navigating to clip detail page
    const params = new URLSearchParams();
    if (teamId) {
      params.set("teamId", teamId);
    }
    const search = searchParams.get("search");
    if (search) {
      params.set("search", search);
    }
    if (searchType && searchType !== "text") {
      params.set("searchType", searchType);
    }

    const queryString = params.toString();
    const url = `/dashboard/create-clips/clip/${clip.id}${
      queryString ? `?${queryString}` : ""
    }`;
    router.push(url);
  };

  const handleEditClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditDialogOpen(true);
  };

  const handleDescriptionUpdated = (newDescription: string) => {
    setDescription(newDescription);
  };

  const onMarkAsFalsePositiv = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      if (isMarkingAsFalsePositive) return;
      setIsMarkingAsFalsePositive(true);
      const effectiveTeamId = teamId || currentTeam?.id;
      const { error } = await markClipAsFalsePositive(
        clip.id,
        effectiveTeamId
      );
      if (error) {
        throw new Error("Error marking clip as false positive: " + error);
      }
      setIsDeleted(true);
      toast.success("Clip marked as false positive");
      router.refresh();
    } catch (error: unknown) {
      const message = getErrorMessage(error);
      console.error("error in onMarkAsFalsePositiv: ", message);
      toast.error(message);
    } finally {
      setIsMarkingAsFalsePositive(false);
    }
  };

  if (isDeleted) return null;

  return (
    <Card
      className="group hover:shadow-md transition-all duration-200 cursor-pointer p-0"
      onClick={handleClick}
    >
      <CardContent className="p-0">
        {/* Video Preview */}
        <div className="relative aspect-video bg-muted rounded-t-lg overflow-hidden">
          <PreviewVideo
            src={clip.clip_url}
            poster={clip.thumbnail_url}
            onClick={handleClick}
            onDurationLoaded={setActualDuration}
          />

          {/* Duration badge */}
          <div className="absolute bottom-2 right-2 bg-foreground/70 text-primary-foreground px-2 py-1 rounded text-sm md:text-xs font-medium">
            <Clock className="h-3 w-3 inline mr-1" />
            {formatDuration(actualDuration ?? clip.duration_seconds)}
          </div>


          <div className="absolute top-2 right-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" aria-label="More Options">
                  <MoreVerticalIcon color="white" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuGroup>
                  {description && canEditDescription && (
                    <DropdownMenuItem onClick={handleEditClick}>
                      <Edit className="h-4 w-4 mr-2" />
                      Edit description
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem
                    onClick={onMarkAsFalsePositiv}
                    variant="destructive"
                  >
                    <CircleAlert className="h-4 w-4 mr-2" />
                    Mark as incorrect
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          {/* Session info */}
          <div className="flex items-center justify-between text-sm md:text-xs text-muted-foreground pt-2">
            {clip.parliament_event?.title && (
              <p className="text-xs text-muted-foreground">{clip.parliament_event.title}</p>
            )}
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4 md:h-3 md:w-3" />
              <span>
                {clip.parliament_event?.session_date
                  ? formatDate(clip.parliament_event.session_date)
                  : clip.session_date
                  ? formatDate(clip.session_date)
                  : formatDate(clip.created_at)}
              </span>
            </div>
          </div>

          {/* Description or Transcript */}
          <div className="space-y-2">
            <p className="text-base md:text-sm text-foreground line-clamp-3 leading-relaxed">
              {description || truncateText(getDisplayTranscript(clip.transcript, clip.transcript_manually_edited), 150)}
            </p>
          </div>
        </div>
      </CardContent>

      {/* Edit Description Dialog */}
      {description && (
        <EditDescriptionDialog
          open={isEditDialogOpen}
          onOpenChange={setIsEditDialogOpen}
          clipId={clip.id}
          currentDescription={description}
          onDescriptionUpdated={handleDescriptionUpdated}
        />
      )}
    </Card>
  );
}
