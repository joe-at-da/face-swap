"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Video,
  MonitorPlay,
  UserCircle,
  MapPin,
  Users2,
  RectangleHorizontal,
  RectangleVertical,
} from "lucide-react";
import Link from "next/link";
import VideoSection from "./video-section";
import MetadataSection from "./metadata-section";
import { SmartAvatar } from "@/components/smart-avatar";
import { DescriptionTranscriptViewer } from "@/app/clips/[clipId]/components/description-transcript-viewer";
import { useCurrentTeam, useIsPersonalMode } from "@/stores/teamStore";
import { use$ } from "@legendapp/state/react";
import { userStore$ } from "@/stores/userStore";
import { Skeleton } from "@/components/ui/skeleton";
import { isMPEmail } from "@/lib/domains";
import { formatFileSize } from "@/lib/formatFileSize";
import { useVideoSize } from "@/hooks/use-video-size";
import type {
  ParliamentMemberClip,
  ParliamentMember,
} from "@/types/parliament";

interface ClipDetailViewProps {
  clip: ParliamentMemberClip;
  mp: ParliamentMember;
  teamId?: string;
  parliamentEvent: { title: string; session_date: string | null } | null;
}

export default function ClipDetailView({
  clip,
  mp,
  teamId,
  parliamentEvent,
}: ClipDetailViewProps) {
  const searchParams = useSearchParams();
  const [actualDuration, setActualDuration] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"horizontal" | "vertical">(
    "horizontal"
  );
  const { horizontalSizeBytes, verticalSizeBytes, isHorizontalLoading, isVerticalLoading } = useVideoSize(
    clip.clip_url,
    clip.vertical_clip_url
  );
  const currentTeam = useCurrentTeam();
  const isPersonalMode = useIsPersonalMode();
  // Get email from session - use$ properly unwraps the observable
  const sessionEmail = use$(userStore$.session.user.email);

  // Track if client has mounted (to avoid hydration mismatch with Legend State stores)
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Check if user can edit description and transcript
  // Only compute after hydration to avoid server/client mismatch
  let canEditDescription = false;
  let canEditTranscript = false;

  if (isMounted) {
    if (isPersonalMode) {
      const userEmail =
        typeof sessionEmail === "string" && sessionEmail ? sessionEmail : null;
      if (userEmail) {
        const canEdit = isMPEmail(userEmail);
        canEditDescription = canEdit;
        canEditTranscript = canEdit;
      }
    } else if (currentTeam) {
      const canEdit =
        currentTeam.userRole === "owner" ||
        currentTeam.userRole === "administrator";
      canEditDescription = canEdit;
      canEditTranscript = canEdit;
    }
  }

  // Build back link with preserved search params
  const getBackLink = () => {
    const from = searchParams.get("from");

    // If navigated from LD Clips page, link back there
    if (from === "ld-clips") {
      const params = new URLSearchParams();
      if (teamId) params.set("teamId", teamId);
      const queryString = params.toString();
      return queryString
        ? `/dashboard/ld-clips?${queryString}`
        : "/dashboard/ld-clips";
    }

    const params = new URLSearchParams();
    if (teamId) {
      params.set("teamId", teamId);
    }
    const search = searchParams.get("search");
    const searchType = searchParams.get("searchType");

    if (search) {
      params.set("search", search);
    }
    if (searchType) {
      params.set("searchType", searchType);
    }

    const queryString = params.toString();
    return queryString
      ? `/dashboard/create-clips?${queryString}`
      : "/dashboard/create-clips";
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Unknown date";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("en-GB", {
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(date);
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "Unknown";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    if (mins > 0) {
      return `${mins} minute${mins !== 1 ? "s" : ""} ${secs} second${
        secs !== 1 ? "s" : ""
      }`;
    }
    return `${secs} second${secs !== 1 ? "s" : ""}`;
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      // Handle duration format like "99:42.555"
      if (timestamp.includes(":") && timestamp.includes(".")) {
        const [minutesStr, secondsWithMs] = timestamp.split(":");
        const [secondsStr] = secondsWithMs.split(".");
        const minutes = parseInt(minutesStr);
        const seconds = parseInt(secondsStr);

        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;

        // Always show in HH:MM:SS format for consistency
        return `${hours.toString().padStart(2, "0")}:${remainingMinutes
          .toString()
          .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
      }

      // Try to parse as date if not duration format
      const date = new Date(timestamp);
      if (!isNaN(date.getTime())) {
        return date.toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
      }

      return timestamp;
    } catch {
      return timestamp;
    }
  };

  const primaryPortrait = mp.parliament_member_portraits?.find(
    (p) => p.is_primary
  )?.image_url;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-4">
        <Button variant="ghost" size="sm" asChild className="group -ml-2">
          <Link href={getBackLink()} className="flex items-center gap-2">
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            <span className="text-sm font-normal">Back to Speech Library</span>
          </Link>
        </Button>

        <div className="space-y-2">
          <h1 className="text-2xl font-sans font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
            {mp.display_name}
          </h1>
          <h2 className="text-base font-sans font-normal text-muted-foreground">
            Created{" "}
            {clip.created_at
              ? formatDate(clip.created_at)
              : "Date not available"}
          </h2>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Video Player */}
          <Card className="border  overflow-hidden">
            <CardHeader>
              <div className="flex items-center sm:flex-row flex-col justify-between">
                <CardTitle className="flex items-center gap-3 text-xl">
                  <div className="p-1 rounded bg-slate-200">
                    <Video className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="text-lg font-sans font-bold">Video Player</h3>
                </CardTitle>
                <div className="flex items-center gap-2 pt-2 sm:pt-0">
                  <Button
                    variant={activeTab === "horizontal" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setActiveTab("horizontal")}
                    disabled={!clip.clip_url}
                    className={`flex items-center gap-2 ${
                      activeTab === "horizontal"
                        ? "bg-primary text-primary-foreground hover:bg-accent-foreground"
                        : ""
                    }`}
                  >
                    <RectangleHorizontal className="h-4 w-4" />
                    Horizontal
                  </Button>
                  <Button
                    variant={activeTab === "vertical" ? "outline" : "outline"}
                    size="sm"
                    onClick={() => setActiveTab("vertical")}
                    disabled={!clip.vertical_clip_url}
                    className={`flex items-center gap-2 ${
                      activeTab === "vertical"
                        ? "bg-white text-foreground border border-border hover:bg-white"
                        : ""
                    }`}
                  >
                    <RectangleVertical className="h-4 w-4" />
                    Vertical
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <VideoSection
                clipUrl={clip.clip_url}
                verticalClipUrl={clip.vertical_clip_url}
                thumbnailUrl={clip.thumbnail_url}
                verticalThumbnailUrl={clip.vertical_thumbnail_url}
                title={`${mp.display_name}`}
                onDurationLoaded={setActualDuration}
                activeTab={activeTab}
              />
            </CardContent>
          </Card>

          {/* Description/Transcript Viewer */}
          {(clip.description || clip.transcript) && (
            <DescriptionTranscriptViewer
              description={clip.description}
              transcript={clip.transcript}
              transcriptManuallyEdited={clip.transcript_manually_edited}
              clipId={clip.id}
              canEditDescription={canEditDescription}
              canEditTranscript={canEditTranscript}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* MP Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-sans font-bold pb-2">
                <span className="bg-slate-200 rounded p-1">
                  <UserCircle className="h-5 w-5" />
                </span>
                Member of Parliament
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <SmartAvatar
                  profileImage={primaryPortrait}
                  firstName={mp.display_name?.split(" ")[0]}
                  lastName={mp.display_name?.split(" ").slice(1).join(" ")}
                  className="h-12 w-12"
                />
                <div className="flex-1">
                  <p className="font-semibold text-sm font-sans pb-2">
                    {mp.display_name}
                  </p>
                  <div className="flex items-center gap-1.5 text-sm text-foreground mt-0.5">
                    <span className="bg-slate-200 rounded p-1">
                      <Users2 className="h-3 w-3" />
                    </span>
                    {(mp.party_name || mp.party_abbreviation) && (
                      <span className="text-foreground font-normal text-sm font-sans">
                        {mp.party_name || mp.party_abbreviation}
                      </span>
                    )}
                  </div>
                  {mp.constituency_name && (
                    <div className="flex items-center gap-1.5 text-sm text-foreground mt-0.5">
                      <span className="bg-slate-200 rounded p-1">
                        <MapPin className="h-3 w-3" />
                      </span>
                      <span>{mp.constituency_name}</span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Clip Details */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 pb-4 text-lg font-sans font-bold">
                  <span className="bg-slate-200 rounded p-1">
                    <MonitorPlay className="h-6 w-6" />
                  </span>
                  Clip Details
                </CardTitle>
                <Badge className="bg-emerald-200 text-emerald-800">
                  {clip.status || "Available"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <div className="flex items-center gap-2 text-foreground">
                  <span>Duration</span>
                </div>
                <span className="font-normal text-sm font-sans">
                  {formatDuration(actualDuration ?? clip.duration_seconds)}
                </span>
              </div>

              {(clip.clip_url || clip.vertical_clip_url) && (
                <div className="flex justify-between items-center text-sm">
                  <div className="flex items-center gap-2 text-foreground">
                    <span>Video Size</span>
                  </div>
                  <span className="font-normal text-sm font-sans">
                    {(activeTab === "horizontal"
                      ? (clip.clip_url ? isHorizontalLoading : isVerticalLoading)
                      : (clip.vertical_clip_url ? isVerticalLoading : isHorizontalLoading)
                    ) ? (
                      <Skeleton className="h-4 w-16 inline-block" />
                    ) : (
                      formatFileSize(
                        activeTab === "horizontal"
                          ? (clip.clip_url ? horizontalSizeBytes : verticalSizeBytes)
                          : (clip.vertical_clip_url ? verticalSizeBytes : horizontalSizeBytes)
                      )
                    )}
                  </span>
                </div>
              )}

              {clip.created_at && (
                <div className="flex justify-between items-center text-sm">
                  <div className="flex items-center gap-2 text-foreground">
                    <span>Date</span>
                  </div>
                  <span className="font-normal text-sm font-sans">
                    {formatDate(
                      parliamentEvent?.session_date ||
                        clip.session_date ||
                        clip.created_at
                    )}
                  </span>
                </div>
              )}

              {parliamentEvent?.title && (
                <div className="flex justify-between items-center text-sm">
                  <div className="text-foreground">
                    <span>Session</span>
                  </div>
                  <span className="text-foreground">
                    {parliamentEvent.title}
                  </span>
                </div>
              )}

              {(clip.start_timestamp || clip.end_timestamp) && (
                <div className="space-y-2 pt-3">
                  <h4 className="font-semibold text-sm flex items-center gap-2">
                    Timestamps
                  </h4>
                  <div className="text-sm space-y-1">
                    {clip.start_timestamp && (
                      <div className="flex justify-between">
                        <span className="text-foreground">Start:</span>
                        <span className="font-normal text-sm text-foreground font-sans">
                          {formatTimestamp(clip.start_timestamp)}
                        </span>
                      </div>
                    )}
                    {clip.end_timestamp && (
                      <div className="flex justify-between">
                        <span className="text-foreground">End:</span>
                        <span className="font-normal text-sm text-foreground font-sans">
                          {formatTimestamp(clip.end_timestamp)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <MetadataSection
            clip={clip}
            mp={mp}
            teamId={teamId}
            actualDuration={actualDuration}
          />
        </div>
      </div>
    </div>
  );
}
