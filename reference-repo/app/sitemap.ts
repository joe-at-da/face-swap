import { MetadataRoute } from "next";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl =
    process.env.NEXT_PUBLIC_FRONTEND_URL || "https://parliamentconnect.com";

  // Normalize baseUrl for comparison (remove trailing slash)
  const normalizedBaseUrl = baseUrl.replace(/\/$/, "");

  // Skip user clips for localhost or staging server
  const isDevEnvironment =
    normalizedBaseUrl.includes("localhost") ||
    normalizedBaseUrl.includes("127.0.0.1") ||
    normalizedBaseUrl === "https://themp.veedoo.dev" ||
    normalizedBaseUrl.includes("themp.veedoo.dev");

  // Fetch all public (non-deleted) user clips only for production
  let clipEntries: MetadataRoute.Sitemap = [];
  if (!isDevEnvironment) {
    const allClips: Array<{ id: string; updated_at: string | null }> = [];
    const pageSize = 1000;
    let offset = 0;
    let hasMore = true;

    // Paginate through all user clips
    while (hasMore) {
      const { data: userClips, error } = await supabaseAdminClient
        .from("user_clips")
        .select("id, updated_at")
        .eq("is_deleted", false)
        .order("updated_at", { ascending: false })
        .range(offset, offset + pageSize - 1);

      if (error) {
        console.error("Error fetching user clips for sitemap:", error);
        break;
      }

      if (userClips && userClips.length > 0) {
        allClips.push(...userClips);
        offset += pageSize;
        hasMore = userClips.length === pageSize;
      } else {
        hasMore = false;
      }
    }

    // Generate sitemap entries for user clips
    clipEntries = allClips.map((clip) => ({
      url: `${baseUrl}/clips/${clip.id}`,
      lastModified: clip.updated_at ? new Date(clip.updated_at) : new Date(),
      changeFrequency: "weekly" as const,
      priority: 0.7,
    }));
  }

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${baseUrl}/contact`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    ...clipEntries,
    // Add more public pages here as needed
    // Note: Private pages (dashboard, setup, etc.) are intentionally excluded
  ];
}
