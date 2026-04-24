"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Play,
  Trash2,
  ExternalLink,
  MoreVertical,
  UserCircle,
  Loader2,
  MonitorPlay,
  Pencil,
  Calendar,
  Clock,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { ClipStatusBadge } from "./clip-status-badge";
import Link from "next/link";
import { toast } from "sonner";
import type { UserClip } from "@/types/user-clips";

interface MyClipsGridProps {
  clips: UserClip[];
  isLoading?: boolean;
  onDeleteClip?: (clipId: string) => void;
  teamId?: string;
  searchTerm?: string;
}

export function MyClipsGrid({
  clips,
  isLoading = false,
  onDeleteClip,
  teamId,
  searchTerm,
}: MyClipsGridProps) {
  const searchParams = useSearchParams();
  const [deletingClipId, setDeletingClipId] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [clipToDelete, setClipToDelete] = useState<string | null>(null);

  const getClipUrl = (clipId: string) => {
    const baseUrl = `/dashboard/my-clips/${clipId}`;
    const params = new URLSearchParams();

    if (teamId) {
      params.set("teamId", teamId);
    }

    // Preserve search and type params if they exist
    const search = searchParams.get("search");
    const type = searchParams.get("type");
    if (search) {
      params.set("search", search);
    }
    if (type) {
      params.set("type", type);
    }

    const queryString = params.toString();
    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(date);
  };

  const formatDateNumeric = (dateString: string) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const formatDuration = (duration: number | string | null): string => {
    if (!duration) return "0:00";

    // Duration is in MM:SS.000 format (e.g., "87:24.949" for 87 minutes and 24 seconds)
    if (typeof duration === "string" && duration.includes(":")) {
      const parts = duration.split(":");
      if (parts.length >= 2) {
        const minutes = parseInt(parts[0]);
        const seconds = parseInt(parts[1].split(".")[0]);
        if (!isNaN(minutes) && !isNaN(seconds)) {
          return `${minutes}:${seconds.toString().padStart(2, "0")}`;
        }
      }
    }

    // Fallback for raw seconds (number input)
    const numSeconds = typeof duration === "string" ? parseFloat(duration) : duration;
    if (isNaN(numSeconds)) return "0:00";
    const mins = Math.floor(numSeconds / 60);
    const secs = Math.floor(numSeconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const formatSessionDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return "";
    try {
      return formatDateNumeric(dateStr);
    } catch {
      return "";
    }
  };

  const handleDeleteClick = (clipId: string) => {
    setClipToDelete(clipId);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!onDeleteClip || !clipToDelete) return;

    setDeletingClipId(clipToDelete);
    setDeleteConfirmOpen(false);

    try {
      await onDeleteClip(clipToDelete);
      toast.success("Clip deleted successfully");
    } catch (error) {
      toast.error("Failed to delete clip");
      console.error("Error deleting clip:", error);
    } finally {
      setDeletingClipId(null);
      setClipToDelete(null);
    }
  };

  const getThumbnailUrl = (clip: UserClip) => {
    return (
      clip.thumbnail_url ||
      clip.vertical_thumbnail_url ||
      "data:image/svg+xml,%3csvg width='320' height='180' xmlns='http://www.w3.org/2000/svg'%3e%3crect width='100%25' height='100%25' fill='%23f1f5f9'/%3e%3ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280' font-family='system-ui' font-size='14'%3eNo thumbnail%3c/text%3e%3c/svg%3e"
    );
  };

  const canViewClip = (clip: UserClip) => {
    return (
      clip.status === "completed" && (clip.clip_url || clip.vertical_clip_url)
    );
  };

  const isProcessing = (clip: UserClip) => {
    return clip.status === "processing" || clip.status === "pending_review";
  };

  if (isLoading && searchTerm) {
    return (
      <Card className="p-8">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto" />
          <div>
            <h3 className="text-lg font-medium">Searching...</h3>
            <p className="text-muted-foreground text-sm">
              Looking for clips matching &ldquo;{searchTerm}&rdquo;
            </p>
          </div>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Card key={i} className="overflow-hidden p-0">
            <div className="aspect-video bg-muted animate-pulse" />
            <CardContent className="p-4">
              <div className="space-y-2">
                <div className="h-4 bg-muted rounded animate-pulse" />
                <div className="h-3 bg-muted rounded w-2/3 animate-pulse" />
                <div className="flex justify-between items-center">
                  <div className="h-5 bg-muted rounded w-16 animate-pulse" />
                  <div className="h-4 bg-muted rounded w-20 animate-pulse" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (clips.length === 0) {
    return (
      <div className="p-8">
        <div className="text-center space-y-4">
          <div className="mx-auto w-8 h-8 bg-slate-200 rounded flex items-center justify-center">
            <MonitorPlay className="h-6 w-6 text-muted-foreground" />
          </div>
          <div>
            <h3 className="text-lg font-bold font-sans py-2">No clips yet</h3>
            <p className="text-foreground text-sm font-normal">
              You haven&apos;t created any clips yet. Start by creating your
              first clip from parliamentary sessions.
            </p>
          </div>
          <Button asChild>
            <Link href="/dashboard/create-clips">
              <Pencil className="h-4 w-4 mr-2" />
              Create Clip
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {clips.map((clip) => (
        <Card
          key={clip.id}
          className={`group overflow-hidden hover:shadow-md transition-shadow p-0 gap-0 ${isProcessing(clip) ? "opacity-90" : ""
            }`}
        >
          {/* Thumbnail */}
          <div className="relative aspect-video bg-muted overflow-hidden">
            {/* Processing Overlay on Thumbnail */}
            {isProcessing(clip) && (
              <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] z-10 flex items-center justify-center">
                <div className="flex flex-col items-center gap-2">
                  <Loader2 className="h-8 w-8 animate-spin text-white" />
                  <span className="text-sm text-white font-medium">Processing...</span>
                </div>
              </div>
            )}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={getThumbnailUrl(clip)}
              alt="Clip thumbnail"
              className="w-full h-full object-cover transition-transform group-hover:scale-105"
            />

            {/* Status Overlay */}
            <div className="absolute top-2 left-2 z-30">
              <ClipStatusBadge status={clip.status} />
            </div>

            {/* Duration badge */}
            {clip.duration && (
              <div className="absolute bottom-2 right-2 bg-white text-foreground px-2 py-1 rounded text-sm md:text-xs font-medium z-30">
                <Clock className="h-3 w-3 inline mr-1" />
                {formatDuration(clip.duration)}
              </div>
            )}

            {/* Action Overlay */}
            <div className="absolute top-2 right-2 z-30" onClick={(e) => e.stopPropagation()}>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="h-8 w-8 p-0 bg-black/50 hover:bg-black/70 border-0"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreVertical className="h-4 w-4 text-white" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem asChild disabled={!canViewClip(clip)}>
                    <Link href={getClipUrl(clip.id)}>
                      <ExternalLink className="h-4 w-4 mr-2" />
                      View Details
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => handleDeleteClick(clip.id)}
                    disabled={deletingClipId === clip.id}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    {deletingClipId === clip.id ? "Deleting..." : "Delete"}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Play Button for Completed Clips */}
            {canViewClip(clip) && (
              <Link href={getClipUrl(clip.id)}>
                <div className="absolute inset-0 bg-black/0 hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100 z-10">
                  <div className="bg-white rounded-full p-3">
                    <Play className="h-8 w-8 text-primary" />
                  </div>
                </div>
              </Link>
            )}

            {/* Clickable Overlay for Processing Clips */}
            {isProcessing(clip) && (
              <Link href={getClipUrl(clip.id)} className="absolute inset-0 z-10" />
            )}
          </div>

          {/* Content */}
          <CardContent className={`px-3 pt-2 pb-3 space-y-2 ${isProcessing(clip) ? "relative" : ""}`}>
            {/* Processing Overlay */}
            {isProcessing(clip) && (
              <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center rounded-b-lg">
                <div className="flex flex-col items-center gap-2">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">Processing...</span>
                </div>
              </div>
            )}

            {/* Session Date */}
            {clip.parliament_member_clips?.session_date && (
              <div className="flex items-center justify-between text-sm md:text-xs text-muted-foreground">
                <div className="flex text-muted-foreground text-sm font-normal items-center gap-1 ml-auto">
                  <Calendar className="h-4 w-4 md:h-3 md:w-3" />
                  <span>
                    {formatSessionDate(clip.parliament_member_clips.session_date)}
                  </span>
                </div>
              </div>
            )}

            {/* MP Information - Show if no title or always show for non-completed */}
            {(!clip.title || clip.status !== "completed") && (
              <div>
                <div className="flex items-center gap-2 min-w-0">
                  <div className="bg-slate-200 rounded p-1 flex-shrink-0">
                    <UserCircle className="h-3 w-3" />
                  </div>
                  <span className="text-sm font-normal text-foreground truncate">
                    {
                      clip.parliament_member_clips.parliament_members
                        .display_name
                    }
                  </span>
                </div>
              </div>
            )}

            {/* Clip Metadata */}
            <div className="space-y-1 text-xs text-foreground">
              <div className="flex items-center gap-1">
                <div className="bg-slate-200 rounded p-1">
                  <MonitorPlay className="h-3 w-3" />
                </div>
                <span className="text-sm font-normal truncate">Created {formatDate(clip.created_at)}</span>
              </div>
            </div>

            {/* Error Message for Failed Clips */}
            {clip.status === "failed" && clip.error_message && (
              <div className="text-xs text-destructive bg-destructive/10 p-2 rounded border">
                {clip.error_message}
              </div>
            )}

          </CardContent>
        </Card>
      ))}

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteConfirmOpen}
        onOpenChange={(open) => {
          setDeleteConfirmOpen(open);
          if (!open) {
            setClipToDelete(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Clip</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this clip? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setClipToDelete(null)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deletingClipId ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
