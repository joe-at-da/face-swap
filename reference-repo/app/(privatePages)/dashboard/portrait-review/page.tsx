import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { redirect } from "next/navigation";
import { PortraitReviewClient } from "./components/portrait-review-client";

// Force dynamic rendering to prevent caching
export const dynamic = "force-dynamic";
export const revalidate = 0;

export type ReviewStats = {
  averageImagesPerMp: number;
  minImagesPerMp: number;
  totalMpsWithImages: number;
};

interface MPWithPortraits {
  member_id: number;
  display_name: string | null;
  primaryImage: {
    id: string;
    image_url: string;
    fallback_url: string | null;
  } | null;
  hasPrimaryImage: boolean;
  otherImages: Array<{
    id: string;
    image_url: string;
    fallback_url: string | null;
  }>;
}

function calculateReviewStats(mps: MPWithPortraits[]): ReviewStats {
  //members-api.parliament.uk/api/Members/40/Portrait?cropType=2&webVersion=false
  const reviewCounts = mps.map((mp) => mp.otherImages.length);
  const countsWithImages = reviewCounts.filter((count) => count > 0);

  if (countsWithImages.length === 0) {
    return {
      averageImagesPerMp: 0,
      minImagesPerMp: 0,
      totalMpsWithImages: 0,
    };
  }

  const total = countsWithImages.reduce((sum, count) => sum + count, 0);
  const average = Number((total / countsWithImages.length).toFixed(1));

  return {
    averageImagesPerMp: average,
    minImagesPerMp: Math.min(...countsWithImages),
    totalMpsWithImages: countsWithImages.length,
  };
}

function buildCompletionMessage(stats: ReviewStats): string {
  return `MP image evaluation has ended. We have around ${stats.averageImagesPerMp} pictures per MP and the lowest MP picture count is ${stats.minImagesPerMp}.`;
}

export default async function PortraitReviewPage() {
  const supabase = await createSupabaseServerClient();

  // Get authenticated user
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // Check if user has @veedoo.io or @veedoo.com email
  const email = user.email;
  if (
    !email ||
    (!email.endsWith("@veedoo.io") && !email.endsWith("@veedoo.com"))
  ) {
    redirect("/dashboard");
  }

  // Fetch all MPs from House of Commons (house_id = 1) with their portraits
  const { data: members, error: membersError } = await supabaseAdminClient
    .from("parliament_members")
    .select("member_id, display_name")
    .eq("is_current_member", true)
    .eq("is_deleted", false)
    .eq("house_id", 1)
    .order("member_id", { ascending: true });

  if (membersError || !members) {
    console.error("Error fetching members:", membersError);
    return (
      <div className="p-8">
        <p className="text-destructive">
          Error loading members. Please try again later.
        </p>
      </div>
    );
  }

  // Fetch all portraits for these members (batch queries to avoid Supabase .in() limit)
  const memberIds = members.map((m) => m.member_id);
  const BATCH_SIZE = 1000; // Supabase limit for .in() queries
  const PAGE_SIZE = 1000; // Supabase default query limit - must paginate to get all results
  const allPortraits: Array<{
    id: string;
    member_id: number;
    image_url: string;
    is_primary: boolean | null;
    is_valid_mp_image?: boolean | null;
  }> = [];

  // Batch the member IDs and fetch all portraits for each batch with pagination
  for (let i = 0; i < memberIds.length; i += BATCH_SIZE) {
    const batch = memberIds.slice(i, i + BATCH_SIZE);
    let hasMore = true;
    let page = 0;
    let useValidationFilter = true; // Track if we should use is_valid_mp_image filter

    // Paginate through portraits for this batch of member IDs
    while (hasMore) {
      const startRange = page * PAGE_SIZE;
      const endRange = startRange + PAGE_SIZE - 1;

      let batchPortraits: Array<{
        id: string;
        member_id: number;
        image_url: string;
        is_primary: boolean | null;
        is_valid_mp_image?: boolean | null;
      }> | null = null;
      let batchError: {
        message?: string;
        code?: string;
        details?: string;
      } | null = null;

      // Try querying with is_valid_mp_image filter first (if we haven't encountered column error)
      if (useValidationFilter) {
        const queryWithValidation = supabaseAdminClient
          .from("parliament_member_portraits")
          .select("id, member_id, image_url, is_primary, is_valid_mp_image")
          .in("member_id", batch)
          .eq("is_deleted", false)
          .eq("is_valid_mp_image", false) // Only fetch non-validated images
          .order("member_id", { ascending: true })
          .order("created_at", { ascending: true })
          .range(startRange, endRange);

        const result = await queryWithValidation;
        if (result.error) {
          batchError = result.error;
        } else if (result.data) {
          batchPortraits = result.data;
        }

        // If error suggests column doesn't exist, switch to fallback for all future pages
        if (batchError) {
          const errorMessage =
            batchError.message ||
            batchError.code ||
            batchError.details ||
            JSON.stringify(batchError);

          if (
            (errorMessage.includes("column") &&
              errorMessage.includes("is_valid_mp_image")) ||
            errorMessage.includes("does not exist")
          ) {
            // Column doesn't exist yet, switch to fallback mode for all pages
            useValidationFilter = false;
            batchError = null; // Reset error to try fallback query
          }
        }
      }

      // Use fallback query if validation filter failed or column doesn't exist
      if (!useValidationFilter || batchError) {
        const fallbackResult = await supabaseAdminClient
          .from("parliament_member_portraits")
          .select("id, member_id, image_url, is_primary, is_valid_mp_image")
          .in("member_id", batch)
          .eq("is_deleted", false)
          .order("member_id", { ascending: true })
          .order("created_at", { ascending: true })
          .range(startRange, endRange);

        if (fallbackResult.error) {
          console.error(
            `Error fetching portraits batch ${i / BATCH_SIZE + 1}, page ${
              page + 1
            }:`,
            fallbackResult.error
          );
          return (
            <div className="p-8">
              <p className="text-destructive">
                Error loading portraits. Please try again later.
              </p>
            </div>
          );
        }
        if (fallbackResult.data) {
          batchPortraits = fallbackResult.data;
          // Filter out validated images client-side (in case column exists but filter wasn't applied)
          batchPortraits = batchPortraits.filter(
            (p) =>
              p.is_valid_mp_image === undefined ||
              p.is_valid_mp_image === null ||
              p.is_valid_mp_image === false
          );
        }
        batchError = null; // Clear error after fallback query
      }

      // Accumulate results
      if (batchPortraits && batchPortraits.length > 0) {
        allPortraits.push(...batchPortraits);
        // If we got fewer than PAGE_SIZE results, we've reached the end
        hasMore = batchPortraits.length === PAGE_SIZE;
        page++;
      } else {
        // No more results
        hasMore = false;
      }
    }
  }

  const portraits = allPortraits;

  // Helper function to transform image URLs and add fallbacks
  const transformImageWithFallback = (
    url: string,
    allPortraits: typeof portraits,
    memberId: number
  ): { url: string; fallbackUrl: string | null } => {
    const isParliament = url.includes("parliament.uk");

    if (isParliament) {
      // Find a non-parliament fallback for this member
      const fallback = allPortraits.find(
        (p) => p.member_id === memberId && !p.image_url?.includes("parliament.uk")
      );

      return {
        url: `/api/proxy-image?url=${encodeURIComponent(url)}`,
        fallbackUrl: fallback?.image_url ?? null,
      };
    }

    return { url, fallbackUrl: null };
  };

  // Organize data: group portraits by member and separate primary from others
  // Safety filter: explicitly exclude any portraits marked as valid (defensive programming)
  const mpsWithPortraits: MPWithPortraits[] = members.map((member) => {
    const memberPortraits = portraits.filter(
      (p) =>
        p.member_id === member.member_id &&
        // Explicitly filter out reviewed images as safety measure
        (p.is_valid_mp_image === undefined ||
          p.is_valid_mp_image === null ||
          p.is_valid_mp_image === false)
    );

    const primary = memberPortraits.find((p) => p.is_primary === true);
    // Only include non-primary images that haven't been reviewed
    const others = memberPortraits.filter(
      (p) =>
        p.is_primary !== true &&
        (p.is_valid_mp_image === undefined ||
          p.is_valid_mp_image === null ||
          p.is_valid_mp_image === false)
    );

    const primaryTransformed = primary
      ? transformImageWithFallback(primary.image_url, portraits, member.member_id)
      : null;

    return {
      member_id: member.member_id,
      display_name: member.display_name,
      primaryImage: primary && primaryTransformed
        ? {
            id: primary.id,
            image_url: primaryTransformed.url,
            fallback_url: primaryTransformed.fallbackUrl,
          }
        : null,
      hasPrimaryImage: Boolean(primary),
      otherImages: others.map((p) => {
        const transformed = transformImageWithFallback(
          p.image_url,
          portraits,
          member.member_id
        );
        return {
          id: p.id,
          image_url: transformed.url,
          fallback_url: transformed.fallbackUrl,
        };
      }),
    };
  });

  const stats = calculateReviewStats(mpsWithPortraits);
  const completionMessage = buildCompletionMessage(stats);

  // Filter out MPs that have no other images to review (only keep those with otherImages.length > 0)
  const mpsToReview = mpsWithPortraits
    .filter((mp) => mp.otherImages.length > 0)
    .sort((a, b) => a.member_id - b.member_id);

  // Calculate total number of images left to evaluate for all MPs
  const totalImagesLeft = mpsWithPortraits.reduce(
    (sum, mp) => sum + mp.otherImages.length,
    0
  );

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-4xl font-serif font-bold text-foreground tracking-tight">
          Portrait Review
        </h1>
        <p className="text-xl text-foreground/80 font-medium leading-relaxed">
          Review and remove unwanted parliament member portrait images.
        </p>
        <p className="text-lg text-muted-foreground font-medium">
          {totalImagesLeft.toLocaleString()} image
          {totalImagesLeft !== 1 ? "s" : ""} left to evaluate for all MPs
        </p>
      </div>

      {mpsToReview.length === 0 ? (
        <div className="p-8 text-center space-y-2">
          <p className="text-lg font-semibold text-foreground">
            MP image evaluation has ended.
          </p>
          <p className="text-muted-foreground">{completionMessage}</p>
          <p className="text-sm text-muted-foreground">
            Average images per MP: {stats.averageImagesPerMp} · Lowest count:{" "}
            {stats.minImagesPerMp}
          </p>
        </div>
      ) : (
        <PortraitReviewClient
          mps={mpsToReview}
          stats={stats}
          completionMessage={completionMessage}
        />
      )}
    </div>
  );
}
