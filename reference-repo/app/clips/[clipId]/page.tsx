import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { after } from "next/server";
import { Calendar, MapPin } from "lucide-react";
import { MpInfoCard } from "./components/mp-info-card";
import { ClipPageFooter } from "./components/clip-page-footer";
import {
  PublicClipInteractive,
  PublicClipVideoViewer,
} from "./components/public-clip-interactive";
import { DescriptionTranscriptViewer } from "./components/description-transcript-viewer";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { incrementViewCount } from "./server-utils";
import type { PublicClipData } from "@/types/user-clips";
import { getDisplayTranscript } from "@/lib/fixTranscriptCapitalization";

interface PageProps {
  params: Promise<{ clipId: string }>;
}

async function fetchPublicClip(clipId: string): Promise<PublicClipData | null> {
  // Validate UUID format
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(clipId)) {
    return null;
  }

  try {
    // Fetch user clip WITHOUT user_id filter (public access)
    const { data: userClip, error: userClipError } = await supabaseAdminClient
      .from("user_clips")
      .select("*")
      .eq("id", clipId)
      .eq("is_deleted", false)
      .single();

    if (userClipError || !userClip) {
      return null;
    }

    // Fetch parliament member clip details
    const { data: parliamentClip, error: parliamentClipError } =
      await supabaseAdminClient
        .from("parliament_member_clips")
        .select(
          `
          id,
          member_id,
          session_type,
          session_date,
          session_uid,
          full_video_path
        `,
        )
        .eq("id", userClip.clip_id)
        .single();

    if (parliamentClipError || !parliamentClip) {
      return null;
    }

    // Fetch parliament event details if session_uid exists
    let parliamentEvent = null;
    if (parliamentClip.session_uid) {
      const { data: eventData, error: eventError } = await supabaseAdminClient
        .from("parliament_events")
        .select("title, session_date")
        .eq("event_id", parliamentClip.session_uid)
        .eq("is_deleted", false)
        .single();

      if (!eventError && eventData) {
        parliamentEvent = eventData;
      }
    }

    // Fetch parliament member details with party colors
    const { data: parliamentMember, error: parliamentMemberError } =
      await supabaseAdminClient
        .from("parliament_members")
        .select(
          `
          member_id,
          display_name,
          full_title,
          party_name,
          party_abbreviation,
          party_background_colour,
          party_foreground_colour,
          constituency_name
        `,
        )
        .eq("member_id", parliamentClip.member_id)
        .single();

    if (parliamentMemberError || !parliamentMember) {
      return null;
    }

    // Fetch parliament member portrait
    const { data: portrait } = await supabaseAdminClient
      .from("parliament_member_portraits")
      .select("image_url")
      .eq("member_id", parliamentClip.member_id)
      .eq("is_deleted", false)
      .eq("is_primary", true)
      .single();

    // Add portrait URL to member data if available
    const memberWithPortrait = {
      ...parliamentMember,
      profile_image: portrait?.image_url || null,
    };

    // Combine the data for public consumption
    const publicClipData: PublicClipData = {
      id: userClip.id,
      created_at: userClip.created_at || new Date().toISOString(),
      status: userClip.status || "completed",
      duration: userClip.duration,
      transcript: userClip.transcript,
      transcript_manually_edited: userClip.transcript_manually_edited ?? false,
      title: userClip.title,
      description: userClip.description,
      clip_url: userClip.clip_url,
      vertical_clip_url: userClip.vertical_clip_url,
      thumbnail_url: userClip.thumbnail_url,
      vertical_thumbnail_url: userClip.vertical_thumbnail_url,
      parliament_event_title: parliamentEvent?.title || null,
      parliament_event_session_date: parliamentEvent?.session_date || null,
      parliament_member_clips: {
        session_type: parliamentClip.session_type,
        session_date: parliamentClip.session_date,
        parliament_members: {
          member_id: memberWithPortrait.member_id,
          display_name: memberWithPortrait.display_name || "Unknown",
          full_title: memberWithPortrait.full_title,
          party_name: memberWithPortrait.party_name,
          party_abbreviation: memberWithPortrait.party_abbreviation,
          party_background_colour: memberWithPortrait.party_background_colour,
          party_foreground_colour: memberWithPortrait.party_foreground_colour,
          constituency_name: memberWithPortrait.constituency_name,
          profile_image: memberWithPortrait.profile_image,
        },
      },
    };

    return publicClipData;
  } catch (error) {
    console.error("Error fetching public clip:", error);
    return null;
  }
}

// Helper function to truncate text for meta descriptions
function truncateText(text: string | null, maxLength: number): string {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3).trim() + "...";
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { clipId } = await params;
  const clip = await fetchPublicClip(clipId);

  if (!clip) {
    return {
      title: "Clip Not Found | Parliament Connect",
      description: "The requested clip could not be found.",
    };
  }

  const mpData = clip.parliament_member_clips?.parliament_members;
  const mpName = mpData?.full_title || mpData?.display_name || "MP";

  // Generate title - use clip title or fallback to MP name
  const title = clip.title || `${mpName} - Parliament Clip`;

  // Generate description - prefer clip description, fallback to transcript
  const description = truncateText(
    clip.description ||
      getDisplayTranscript(clip.transcript, clip.transcript_manually_edited) ||
      `Watch this Parliament clip featuring ${mpName}`,
    160,
  );

  // Get thumbnail URL - prefer horizontal for social sharing
  const imageUrl = clip.thumbnail_url || clip.vertical_thumbnail_url;

  // Base URL for absolute URLs
  const baseUrl =
    process.env.NEXT_PUBLIC_FRONTEND_URL ||
    (process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : "http://localhost:3000");
  const clipUrl = `${baseUrl}/clips/${clipId}`;

  return {
    title: `${title} | Parliament Connect`,
    description,
    openGraph: {
      title,
      description,
      url: clipUrl,
      siteName: "Parliament Connect",
      type: "video.other",
      ...(imageUrl && {
        images: [
          {
            url: imageUrl,
            width: 1280,
            height: 720,
            alt: title,
          },
        ],
      }),
      ...(clip.clip_url && {
        videos: [
          {
            url: clip.clip_url,
            width: 1280,
            height: 720,
            type: "video/mp4",
          },
        ],
      }),
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      ...(imageUrl && { images: [imageUrl] }),
    },
  };
}

// Helper function to format hex colors (add # if missing)
function formatHexColor(color: string | null): string | null {
  if (!color) return null;
  return color.startsWith("#") ? color : `#${color}`;
}

export default async function PublicClipPage({ params }: PageProps) {
  const { clipId } = await params;
  const clip = await fetchPublicClip(clipId);

  if (!clip) {
    notFound();
  }

  // Schedule view count increment to run after response is sent
  after(() => {
    incrementViewCount(clipId);
  });

  const mpData = clip.parliament_member_clips?.parliament_members;
  const clipDetails = clip.parliament_member_clips;
  // Generate public URL - use environment variable if available
  const baseUrl =
    process.env.NEXT_PUBLIC_FRONTEND_URL ||
    (process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : "http://localhost:3000");
  const publicUrl = `${baseUrl}/clips/${clipId}`;

  // Page title for sharing - use clip title if available, otherwise fallback
  const pageTitle =
    clip.title ||
    `${mpData?.full_title || mpData?.display_name} - Parliament Clip`;

  // Display title for the h1 - use clip.title with fallback
  const displayTitle =
    clip.title ||
    `${mpData?.full_title || mpData?.display_name} - Parliament Clip`;

  // Session date from parliament_events, fallback to parliament_member_clips.session_date
  const sessionDate =
    clip.parliament_event_session_date || clipDetails?.session_date;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header and Share Dialog - Client Component */}
      <PublicClipInteractive
        clip={clip}
        clipId={clipId}
        publicUrl={publicUrl}
        pageTitle={pageTitle}
      />

      {/* Main Content */}
      <main className="flex-1">
        <div className="container mx-auto px-4 md:px-6 lg:px-8 py-10 max-w-7xl">
          <div className="grid gap-8 lg:grid-cols-[2fr_320px]">
            {/* Left Column - Video and Details */}
            <div className="space-y-8">
              {/* Party Badge - Full Width */}
              {mpData?.party_name && (
                <div
                  className="w-full rounded-xl px-6 py-3 text-center"
                  style={{
                    backgroundColor:
                      formatHexColor(mpData.party_background_colour) ||
                      "#3b82f6",
                    color:
                      formatHexColor(mpData.party_foreground_colour) ||
                      "#ffffff",
                  }}
                >
                  <h2 className="font-semibold text-lg">{mpData.party_name}</h2>
                </div>
              )}

              {/* Video Player - Client Component */}
              <PublicClipVideoViewer clip={clip} />

              {/* Title */}
              <div className="space-y-4">
                <h1 className="text-3xl md:text-4xl font-bold leading-tight">
                  {displayTitle}
                </h1>

                {/* Metadata */}
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  {sessionDate && (
                    <div className="flex items-center gap-1.5">
                      <Calendar className="h-4 w-4" />
                      <span>
                        {new Date(sessionDate).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "long",
                          year: "numeric",
                        })}
                      </span>
                    </div>
                  )}
                  {clip.parliament_event_title && (
                    <div className="flex items-center gap-1.5">
                      <MapPin className="h-4 w-4" />
                      <span>{clip.parliament_event_title}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Description/Transcript Switcher */}
              {(clip.description || clip.transcript) && (
                <DescriptionTranscriptViewer
                  description={clip.description}
                  transcript={clip.transcript}
                  transcriptManuallyEdited={clip.transcript_manually_edited}
                />
              )}
            </div>

            {/* Right Column - MP Info (Desktop only) */}
            <div className="hidden lg:block lg:sticky lg:top-6 h-fit">
              <MpInfoCard
                mpName={
                  mpData?.full_title || mpData?.display_name || "Unknown MP"
                }
                constituency={mpData?.constituency_name || null}
                profileImage={mpData?.profile_image || null}
                isMP={true}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <ClipPageFooter />
    </div>
  );
}
