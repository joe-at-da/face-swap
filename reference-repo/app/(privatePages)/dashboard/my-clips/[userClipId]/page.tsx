"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  Loader2,
  Copy,
  Check,
  Pencil,
  MapPin,
  Users2,
  Link as LinkIcon,
} from "lucide-react";
import { SmartAvatar } from "@/components/smart-avatar";
import Link from "next/link";
import {
  ClipProcessingStatus,
  ClipProcessingEstimatedTime,
} from "./components/clip-processing-status";
import { ClipViewer } from "./components/clip-viewer";
import { ClipShareLinks } from "./components/clip-share-links";
import { ClipDownloadSection } from "./components/clip-download-section";
import { ClipTranscript } from "./components/clip-transcript";
import { SocialShareButtons } from "./components/social-share-buttons";
import { ClipMetadataPanel } from "./components/clip-metadata-panel";
import { EditTitleDialog } from "./components/edit-title-dialog";
import { toast } from "sonner";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import type { RealtimeChannel } from "@supabase/supabase-js";
import type { UserClipData } from "@/types/user-clips";
import { canEditUserClip } from "@/lib/clip-permissions";

export default function UserClipPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const userClipId = params?.userClipId as string;

  // Build back link with preserved search params
  const getBackLink = () => {
    const urlParams = new URLSearchParams();
    const search = searchParams.get("search");
    const type = searchParams.get("type");
    const teamId = searchParams.get("teamId");

    if (search) {
      urlParams.set("search", search);
    }
    if (type) {
      urlParams.set("type", type);
    }
    if (teamId) {
      urlParams.set("teamId", teamId);
    }

    const queryString = urlParams.toString();
    return queryString
      ? `/dashboard/my-clips?${queryString}`
      : "/dashboard/my-clips";
  };

  const [clip, setClip] = useState<UserClipData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [avgProcessingTime, setAvgProcessingTime] = useState<number>(60);
  const [canEdit, setCanEdit] = useState<boolean>(false);
  const [isEditTitleDialogOpen, setIsEditTitleDialogOpen] = useState(false);
  const [copiedTitle, setCopiedTitle] = useState(false);
  const channelRef = useRef<RealtimeChannel | null>(null);

  // Fetch initial clip data
  useEffect(() => {
    const fetchClip = async () => {
      if (!userClipId) return;

      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(`/api/user-clips/${userClipId}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch clip");
        }

        setClip(data.data);

        // Check edit permissions
        if (data.data) {
          const hasEditPermission = await canEditUserClip(data.data);
          setCanEdit(hasEditPermission);
        }
      } catch (error) {
        console.error("Error fetching clip:", error);
        setError(
          error instanceof Error ? error.message : "Failed to load clip",
        );
        toast.error("Failed to load clip details");
      } finally {
        setIsLoading(false);
      }
    };

    fetchClip();
  }, [userClipId]);

  // Fetch processing stats
  useEffect(() => {
    const fetchProcessingStats = async () => {
      try {
        const response = await fetch("/api/clips/processing-stats");
        const data = await response.json();

        if (data.success && data.data) {
          setAvgProcessingTime(data.data.average_processing_time_seconds);
        }
      } catch (error) {
        console.error("Error fetching processing stats:", error);
      }
    };

    fetchProcessingStats();
  }, []);

  // Subscribe to Supabase realtime updates for this specific user clip
  useEffect(() => {
    if (!userClipId) return;

    const supabase = createSupabaseBrowserClient();

    const setupRealtime = async () => {
      try {
        const {
          data: { session },
          error: authError,
        } = await supabase.auth.getSession();

        if (authError || !session) {
          return;
        }

        // Set auth token for realtime before subscribing
        await supabase.realtime.setAuth(session.access_token);

        const channel = supabase
          .channel(`user-clip-${userClipId}`)
          .on(
            "postgres_changes",
            {
              event: "UPDATE",
              schema: "public",
              table: "user_clips",
              filter: `id=eq.${userClipId}`,
            },
            (payload) => {
              if (!payload.new) {
                return;
              }

              const updatedClip = payload.new as Partial<UserClipData>;

              // Update clip state - preserve nested objects if they exist
              setClip((prevClip) => {
                if (!prevClip) return null;
                return {
                  ...prevClip,
                  ...updatedClip,
                  parliament_member_clips:
                    updatedClip.parliament_member_clips ||
                    prevClip.parliament_member_clips,
                };
              });

              // Show toast notifications for status changes
              if (updatedClip.status === "completed") {
                toast.success("Your clip is ready!");
              } else if (updatedClip.status === "failed") {
                toast.error("Clip processing failed");
              }
            },
          )
          .subscribe();

        channelRef.current = channel;
      } catch (error) {
        console.error("Error setting up realtime subscription:", error);
      }
    };

    setupRealtime();

    // Cleanup subscription on unmount or when userClipId changes
    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [userClipId]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" asChild>
            <Link href="/dashboard/my-clips">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to My Clips
            </Link>
          </Button>
        </div>

        {/* Loading State */}
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="text-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Loading clip details...</h3>
              <p className="text-muted-foreground text-sm">
                Please wait while we fetch your clip information.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !clip) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" asChild>
            <Link href="/dashboard/my-clips">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to My Clips
            </Link>
          </Button>
        </div>

        {/* Error State */}
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="text-center space-y-4">
            <div className="text-destructive">
              <h3 className="text-3xl font-serif font-bold">Clip not found</h3>
              <p className="text-sm mt-2">
                This clip may have been removed or is no longer available.
                Please check your My Clips page for your active clips.
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => window.location.reload()}
              >
                Try Again
              </Button>
              <Button asChild>
                <Link href="/dashboard/my-clips">Back to My Clips</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isCompleted = clip.status === "completed";
  const hasVideoContent = Boolean(clip.clip_url || clip.vertical_clip_url);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <Button variant="ghost" size="sm" asChild className="group -ml-2">
          <Link href={getBackLink()} className="flex items-center gap-2">
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            <span>Back to My Clips</span>
          </Link>
        </Button>
      </div>

      {/* MP Name and Date Header */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-4">
        {/* H1 Title - First Column */}
        <div className="lg:col-span-2 space-y-1 flex items-center justify-between">
          <h1
            className="text-2xl font-bold text-foreground tracking-tight"
            style={{ fontFamily: "var(--font-family-sans, Inter)" }}
          >
            {clip.title ||
              clip.parliament_member_clips.parliament_members.display_name}
          </h1>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={async () => {
                const titleText =
                  clip.title ||
                  clip.parliament_member_clips.parliament_members.display_name;
                try {
                  await navigator.clipboard.writeText(titleText);
                  toast.success("Title copied to clipboard!");
                  setCopiedTitle(true);
                  setTimeout(() => setCopiedTitle(false), 2000);
                } catch {
                  toast.error("Failed to copy title");
                }
              }}
              title="Copy title"
            >
              {copiedTitle ? (
                <Check className="h-4 w-4 text-slate-500" />
              ) : (
                <Copy className="h-4 w-4 text-slate-500" />
              )}
            </Button>
            {canEdit && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setIsEditTitleDialogOpen(true)}
                title="Edit title"
              >
                <Pencil className="h-4 w-4 text-slate-500" />
              </Button>
            )}
            <Button
              variant="default"
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={async (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (!clip) {
                  toast.error("Clip not loaded");
                  return;
                }
                const baseUrl =
                  process.env.NEXT_PUBLIC_FRONTEND_URL ||
                  (typeof window !== "undefined"
                    ? window.location.origin
                    : "http://localhost:3000");
                const publicUrl = `${baseUrl}/clips/${clip.id}`;
                try {
                  await navigator.clipboard.writeText(publicUrl);
                  toast.success("URL is copied to clipboard", {
                    icon: <Check className="h-4 w-4" />,
                  });
                } catch (error) {
                  console.error("Failed to copy URL:", error);
                  toast.error("Failed to copy URL");
                }
              }}
            >
              <LinkIcon className="h-4 w-4 mr-2" />
              Copy Video Link
            </Button>
          </div>
        </div>

        {/* MP Information Section - Third Column (Right Side, same row as H1) */}
        <div className="py-2 overflow-hidden">
          <div className="px-4 py-2 space-y-4">
            <div className="flex items-start gap-4">
              <SmartAvatar
                mpPortraitUrl={
                  clip.parliament_member_clips.parliament_members.profile_image
                }
                firstName={
                  clip.parliament_member_clips.parliament_members.display_name.split(
                    " ",
                  )[0] || ""
                }
                lastName={
                  clip.parliament_member_clips.parliament_members.display_name
                    .split(" ")
                    .slice(-1)[0] || ""
                }
                email=""
                isMP={true}
                className="h-16 w-16 text-lg border-2 border-border"
                enableLazyLoading={true}
              />
              <div className="flex-1 min-w-0 space-y-2">
                <div>
                  <h3 className="font-semibold text-sm font-sans leading-tight pb-1">
                    {
                      clip.parliament_member_clips.parliament_members
                        .display_name
                    }
                  </h3>
                  {clip.parliament_member_clips.parliament_members
                    .constituency_name && (
                    <div className="flex items-center gap-1.5 text-xs text-foreground mt-0.5">
                      <span className="bg-slate-200 rounded p-1">
                        <MapPin className="h-3 w-3" />
                      </span>
                      <span className="font-normal">
                        {
                          clip.parliament_member_clips.parliament_members
                            .constituency_name
                        }
                      </span>
                    </div>
                  )}

                  {clip.parliament_member_clips.parliament_members
                    .party_name && (
                    <div className="flex items-center gap-1.5 text-xs text-foreground mt-0.5">
                      <span className="bg-slate-200 rounded p-1">
                        <Users2 className="h-3 w-3" />
                      </span>
                      <span className="font-normal">
                        {
                          clip.parliament_member_clips.parliament_members
                            .party_name
                        }
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Processing Status - Full Width */}
      {!isCompleted && (
        <div className="space-y-4">
          <ClipProcessingStatus
            status={clip.status}
            created_at={clip.created_at}
            updated_at={clip.updated_at}
            error_message={clip.error_message}
            clip_url={clip.clip_url}
            vertical_clip_url={clip.vertical_clip_url}
          />
          {/* Estimated Time */}
          {(() => {
            // Calculate remaining seconds for estimated time
            const calculateRemainingSeconds = () => {
              if (clip.status === "pending_review") return 0;
              if (clip.status !== "processing") return 0;

              const createdTime = new Date(clip.created_at).getTime();
              const now = Date.now();
              const elapsedSeconds = Math.floor((now - createdTime) / 1000);
              const remaining = Math.max(0, avgProcessingTime - elapsedSeconds);
              return remaining;
            };

            return (
              <ClipProcessingEstimatedTime
                status={clip.status}
                remainingSeconds={calculateRemainingSeconds()}
              />
            );
          })()}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-4">
          {/* Video Player */}
          {isCompleted && hasVideoContent && (
            <ClipViewer
              clip_url={clip.clip_url}
              vertical_clip_url={clip.vertical_clip_url}
              thumbnail_url={clip.thumbnail_url}
              vertical_thumbnail_url={clip.vertical_thumbnail_url}
              duration={clip.duration}
              watermark_url={clip.watermark_url}
              watermark_position={clip.watermark_position}
              title={clip.title}
              defaultTitle={
                clip.parliament_member_clips.parliament_members.display_name
              }
              canEdit={canEdit}
              onEditClick={() => setIsEditTitleDialogOpen(true)}
            />
          )}

          {/* Transcript/Description */}
          <ClipTranscript
            transcript={clip.transcript}
            transcriptManuallyEdited={clip.transcript_manually_edited}
            description={clip.description}
            clipId={clip.id}
            canEdit={canEdit}
            onDescriptionUpdate={(newDescription) => {
              setClip((prev) =>
                prev ? { ...prev, description: newDescription } : null,
              );
            }}
            onTranscriptUpdate={(newTranscript) => {
              setClip((prev) =>
                prev ? { ...prev, transcript: newTranscript, transcript_manually_edited: true } : null,
              );
            }}
          />
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Parliament Member and Clip Details */}
          <ClipMetadataPanel clip={clip} />

          {/* Social Sharing */}
          {isCompleted && (
            <SocialShareButtons
              clipUrl={clip.clip_url}
              verticalClipUrl={clip.vertical_clip_url}
              duration={clip.duration}
              mpName={
                clip.parliament_member_clips.parliament_members.display_name
              }
              clipId={clip.id}
              teamId={clip.team_id}
              description={clip.description}
            />
          )}

          {/* Download Section */}
          {isCompleted && (
            <ClipDownloadSection
              clip_url={clip.clip_url}
              vertical_clip_url={clip.vertical_clip_url}
              clipId={clip.id}
            />
          )}

          {/* Share Links */}
          {isCompleted && <ClipShareLinks clipId={clip.id} />}
        </div>
      </div>

      {/* Edit Title Dialog */}
      {clip && (
        <EditTitleDialog
          open={isEditTitleDialogOpen}
          onOpenChange={setIsEditTitleDialogOpen}
          clipId={clip.id}
          currentTitle={clip.title}
          onUpdate={(newTitle) => {
            setClip((prev) => (prev ? { ...prev, title: newTitle } : null));
          }}
        />
      )}
    </div>
  );
}
