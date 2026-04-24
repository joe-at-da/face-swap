import { notFound } from "next/navigation";

interface PageProps {
  params: Promise<{ clipId: string }>;
  searchParams: Promise<{ autoplay?: string }>;
}

async function fetchPublicClip(clipId: string) {
  const baseUrl =
    process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3000";
  const response = await fetch(`${baseUrl}/api/clips/${clipId}/public`, {
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  const { data } = await response.json();
  return data;
}

export default async function EmbedClipPage({
  params,
  searchParams,
}: PageProps) {
  const { clipId } = await params;
  const { autoplay } = await searchParams;

  const clip = await fetchPublicClip(clipId);

  if (!clip || clip.status !== "completed") {
    notFound();
  }

  const shouldAutoplay = autoplay === "true";
  const videoUrl = clip.vertical_clip_url || clip.clip_url;
  const posterUrl = clip.vertical_thumbnail_url || clip.thumbnail_url;

  if (!videoUrl) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-white text-sm">Video not available</p>
      </div>
    );
  }

  const mpName = clip.parliament_member_clips?.parliament_members?.display_name;

  return (
    <div className="relative w-full h-screen flex flex-col">
      {/* Video Player */}
      <div className="flex-1 flex items-center justify-center">
        <video
          controls
          autoPlay={shouldAutoplay}
          poster={posterUrl || undefined}
          className="w-full h-full object-contain"
          playsInline
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      </div>

      {/* Branding Watermark */}
      <div className="absolute bottom-4 left-4 bg-black/70 backdrop-blur-sm rounded px-3 py-2">
        <p className="text-white text-xs font-medium">
          {mpName} - Parliament Connect
        </p>
      </div>
    </div>
  );
}

// Generate metadata for embeds
export async function generateMetadata({ params }: PageProps) {
  const { clipId } = await params;
  const clip = await fetchPublicClip(clipId);

  if (!clip) {
    return {
      title: "Clip Not Found",
    };
  }

  const mpName = clip.parliament_member_clips?.parliament_members?.display_name;

  return {
    title: `${mpName} - Parliament Clip`,
    robots: "noindex, nofollow", // Don't index embed pages
  };
}
