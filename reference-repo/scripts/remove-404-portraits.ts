#!/usr/bin/env tsx

// Load environment variables from .env file
import "dotenv/config";

import { createClient } from "@supabase/supabase-js";
import { Database, Tables } from "@/supabaseTypes";

// Create Supabase client for scripts (without server-only)
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:55321";
const supabaseKey = process.env.SUPABASE_SERVICE_KEY || "";

if (!supabaseKey) {
  console.warn(
    "Warning: SUPABASE_SERVICE_KEY not set. Using default local Supabase key.",
  );
}

const supabaseAdminClient = createClient<Database>(
  supabaseUrl,
  supabaseKey ||
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  },
);

type Portrait = Tables<"parliament_member_portraits">;

// Configuration
const PAGE_SIZE = 1000; // Supabase default limit
const REQUEST_TIMEOUT = 15000; // 15 seconds timeout (matching parliament service)
const DELETE_BATCH_SIZE = 100; // Batch size for soft deletions

// Rate limiting (matching parliament-api-service.ts)
const BURST_LIMIT = 4; // Max 4 requests per second
const MIN_REQUEST_INTERVAL = 500; // Minimum 500ms between requests
const CONCURRENT_REQUESTS = 4; // Match burst limit

// Check for dry-run mode
const isDryRun = process.argv.includes("--dry-run");

// Statistics tracking
interface Stats {
  totalChecked: number;
  totalFailed: number;
  totalDeleted: number;
  primaryPortraitsFailed: number;
  primaryPortraitsDeleted: number;
  failedUrls: string[];
  errors: string[];
}

// Utility function to sleep
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Check if an image URL returns 404 or error
async function checkImageUrl(imageUrl: string): Promise<{
  isValid: boolean;
  statusCode?: number;
  error?: string;
}> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    const response = await fetch(imageUrl, {
      method: "HEAD", // Use HEAD to avoid downloading the full image
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // If HEAD is not supported, try GET but only read headers
    if (response.status === 405 || response.status === 501) {
      const getController = new AbortController();
      const getTimeoutId = setTimeout(
        () => getController.abort(),
        REQUEST_TIMEOUT,
      );

      const getResponse = await fetch(imageUrl, {
        method: "GET",
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          Range: "bytes=0-0", // Only request first byte
        },
        signal: getController.signal,
      });
      clearTimeout(getTimeoutId);

      if (!getResponse.ok) {
        return {
          isValid: false,
          statusCode: getResponse.status,
          error: `HTTP ${getResponse.status}`,
        };
      }

      // Check content type for GET response
      const contentType = getResponse.headers.get("content-type") || "";
      if (!contentType.startsWith("image/")) {
        return {
          isValid: false,
          statusCode: getResponse.status,
          error: `Not an image (content-type: ${contentType})`,
        };
      }

      return { isValid: true, statusCode: getResponse.status };
    } else if (!response.ok) {
      return {
        isValid: false,
        statusCode: response.status,
        error: `HTTP ${response.status}`,
      };
    }

    // Check content type to ensure it's an image
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.startsWith("image/")) {
      return {
        isValid: false,
        statusCode: response.status,
        error: `Not an image (content-type: ${contentType})`,
      };
    }

    return { isValid: true, statusCode: response.status };
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === "AbortError") {
        return {
          isValid: false,
          error: "Request timeout",
        };
      }
      return {
        isValid: false,
        error: error.message,
      };
    }
    return {
      isValid: false,
      error: String(error),
    };
  }
}

// Soft delete portraits in batch (set is_deleted = true and deleted_at = now())
async function softDeletePortraitsBatch(
  portraitIds: string[],
): Promise<number> {
  if (portraitIds.length === 0) return 0;

  // Filter out any invalid IDs
  const validIds = portraitIds.filter((id) => id && typeof id === "string");
  if (validIds.length === 0) {
    console.error("No valid portrait IDs in batch");
    return 0;
  }

  const {
    data,
    error,
    count: _count,
  } = await supabaseAdminClient
    .from("parliament_member_portraits")
    .update({
      is_deleted: true,
      deleted_at: new Date().toISOString(),
    })
    .in("id", validIds)
    .select("id");

  if (error) {
    console.error(
      `Failed to soft delete batch of ${validIds.length} portraits:`,
      error,
    );
    console.error("Error details:", JSON.stringify(error, null, 2));
    return 0;
  }

  // Supabase returns the updated rows in data when using select
  // Count the actual number of rows updated
  if (data && Array.isArray(data)) {
    const updatedCount = data.length;
    if (updatedCount !== validIds.length) {
      console.log(
        `  Note: Updated ${updatedCount} out of ${validIds.length} portraits in batch (some may already be deleted)`,
      );
    }
    return updatedCount;
  }

  // If no data returned but no error, something might be wrong
  // Log a warning but don't fail
  console.warn(
    `  Warning: Update completed but no data returned for batch of ${validIds.length} portraits`,
  );
  return 0;
}

// Rate limiting state (matching parliament-api-service.ts)
let requestTimestamps: number[] = [];
let lastRequestTime = 0;

// Wait for rate limit (matching parliament-api-service.ts logic)
async function waitForRateLimit(): Promise<void> {
  const now = Date.now();

  // Clean old timestamps (older than 1 second for burst calculation)
  requestTimestamps = requestTimestamps.filter(
    (timestamp) => now - timestamp < 1000,
  );

  // Check burst limit (max 4 requests in last second)
  if (requestTimestamps.length >= BURST_LIMIT) {
    const oldestInBurst = requestTimestamps[0];
    const waitTime = 1000 - (now - oldestInBurst) + 5; // Wait until burst window clears + 5ms buffer
    await sleep(waitTime);
    return waitForRateLimit(); // Recheck after waiting
  }

  // Check RPS limit (minimum interval between requests)
  const timeSinceLastRequest = now - lastRequestTime;
  if (timeSinceLastRequest < MIN_REQUEST_INTERVAL) {
    const waitTime = MIN_REQUEST_INTERVAL - timeSinceLastRequest;
    await sleep(waitTime);
  }

  // Record this request
  lastRequestTime = Date.now();
  requestTimestamps.push(lastRequestTime);
}

// Process items in parallel with concurrency limit and rate limiting
async function processInParallel<T, R>(
  items: T[],
  processor: (item: T, index: number) => Promise<R>,
  concurrency: number,
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  const executing: Array<{ promise: Promise<void>; index: number }> = [];
  let completedCount = 0;
  const startTime = Date.now();
  let lastProgressUpdate = 0;

  return new Promise((resolve) => {
    let currentIndex = 0;

    function updateProgress() {
      completedCount++;
      if (
        completedCount - lastProgressUpdate >= 100 ||
        completedCount === items.length
      ) {
        const elapsed = (Date.now() - startTime) / 1000;
        const rate = elapsed > 0 ? (completedCount / elapsed).toFixed(1) : "0";
        console.log(
          `  Progress: ${completedCount}/${items.length} checked (${rate}/s)`,
        );
        lastProgressUpdate = completedCount;
      }
    }

    async function processNext() {
      if (currentIndex >= items.length && executing.length === 0) {
        resolve(results);
        return;
      }

      while (executing.length < concurrency && currentIndex < items.length) {
        // Wait for rate limit before starting new request
        await waitForRateLimit();

        const index = currentIndex++;
        const item = items[index];
        const promise = processor(item, index)
          .then((result) => {
            results[index] = result;
            updateProgress();
            // Remove this promise from executing array
            const execIndex = executing.findIndex((e) => e.index === index);
            if (execIndex !== -1) {
              executing.splice(execIndex, 1);
            }
            processNext();
          })
          .catch((error) => {
            console.error(`Error processing item ${index}:`, error);
            results[index] = null as R;
            updateProgress();
            const execIndex = executing.findIndex((e) => e.index === index);
            if (execIndex !== -1) {
              executing.splice(execIndex, 1);
            }
            processNext();
          });

        executing.push({ promise, index });
      }
    }

    processNext();
  });
}

// Main function
async function main() {
  console.log("Starting 404 portrait removal script...");
  console.log(
    `Mode: ${
      isDryRun ? "DRY RUN (preview only)" : "PRODUCTION (will soft delete)"
    }`,
  );
  console.log("");

  const stats: Stats = {
    totalChecked: 0,
    totalFailed: 0,
    totalDeleted: 0,
    primaryPortraitsFailed: 0,
    primaryPortraitsDeleted: 0,
    failedUrls: [],
    errors: [],
  };

  // First, fetch all member IDs with house_id = 1
  console.log("Fetching member IDs with house_id = 1...");
  const memberIdsWithHouse1: number[] = [];
  let memberPage = 0;
  let hasMoreMembers = true;

  while (hasMoreMembers) {
    const startRange = memberPage * PAGE_SIZE;
    const endRange = startRange + PAGE_SIZE - 1;

    const { data: members, error: membersError } = await supabaseAdminClient
      .from("parliament_members")
      .select("member_id")
      .eq("house_id", 1)
      .eq("is_deleted", false)
      .order("member_id", { ascending: true })
      .range(startRange, endRange);

    if (membersError) {
      console.error("Error fetching members:", membersError);
      process.exit(1);
    }

    if (!members || members.length === 0) {
      hasMoreMembers = false;
      break;
    }

    memberIdsWithHouse1.push(...members.map((m) => m.member_id));
    console.log(
      `  Fetched page ${memberPage + 1}: ${
        members.length
      } members (range ${startRange}-${endRange}, total: ${
        memberIdsWithHouse1.length
      })`,
    );

    if (members.length < PAGE_SIZE) {
      hasMoreMembers = false;
    } else {
      memberPage++;
    }
  }

  console.log(
    `\nFound ${memberIdsWithHouse1.length} members with house_id = 1\n`,
  );

  if (memberIdsWithHouse1.length === 0) {
    console.log("No members found with house_id = 1");
    process.exit(0);
  }

  // Fetch all portraits with members-api.parliament.uk URLs for these members with pagination
  let page = 0;
  let hasMore = true;
  const allPortraits: Portrait[] = [];

  console.log("Fetching portraits from database...");

  // Process member IDs in batches to avoid query size limits
  const MEMBER_BATCH_SIZE = 1000; // Supabase has limits on IN clause size
  for (
    let batchStart = 0;
    batchStart < memberIdsWithHouse1.length;
    batchStart += MEMBER_BATCH_SIZE
  ) {
    const batchEnd = Math.min(
      batchStart + MEMBER_BATCH_SIZE,
      memberIdsWithHouse1.length,
    );
    const memberBatch = memberIdsWithHouse1.slice(batchStart, batchEnd);

    page = 0;
    hasMore = true;

    while (hasMore) {
      const startRange = page * PAGE_SIZE;
      const endRange = startRange + PAGE_SIZE - 1;

      const { data: portraits, error } = await supabaseAdminClient
        .from("parliament_member_portraits")
        .select("id, image_url, member_id, is_primary")
        .in("member_id", memberBatch)
        .ilike("image_url", "%members-api.parliament.uk%")
        .eq("is_deleted", false)
        .order("id", { ascending: true })
        .range(startRange, endRange);

      if (error) {
        console.error("Error fetching portraits:", error);
        process.exit(1);
      }

      if (!portraits || portraits.length === 0) {
        hasMore = false;
        break;
      }

      allPortraits.push(...(portraits as Portrait[]));
      console.log(
        `  Fetched batch ${
          Math.floor(batchStart / MEMBER_BATCH_SIZE) + 1
        }, page ${page + 1}: ${
          portraits.length
        } portraits (range ${startRange}-${endRange}, total: ${
          allPortraits.length
        })`,
      );

      // Continue to next page if we got exactly PAGE_SIZE results (might be more)
      if (portraits.length < PAGE_SIZE) {
        hasMore = false;
      } else {
        page++;
      }
    }
  }

  console.log(`\nFound ${allPortraits.length} portraits to check\n`);

  if (allPortraits.length === 0) {
    console.log("No portraits found matching criteria");
    process.exit(0);
  }

  // Check each portrait URL in parallel with rate limiting
  console.log(
    `Checking image URLs (${CONCURRENT_REQUESTS} concurrent requests, max ${BURST_LIMIT}/sec, ${MIN_REQUEST_INTERVAL}ms min interval)...`,
  );

  // Process portraits in parallel with concurrency limit
  const checkResults = await processInParallel(
    allPortraits,
    async (portrait) => {
      // Safety check for undefined portrait
      if (!portrait || !portrait.image_url) {
        console.error("Invalid portrait data:", portrait);
        return null;
      }

      const checkResult = await checkImageUrl(portrait.image_url);
      if (!checkResult.isValid) {
        return { portrait, checkResult };
      }
      return null;
    },
    CONCURRENT_REQUESTS,
  );

  const portraitsToDelete: Portrait[] = [];

  // Process results
  for (const result of checkResults) {
    if (result) {
      const { portrait, checkResult } = result;

      // Safety check
      if (!portrait || !portrait.image_url) {
        console.error("Skipping invalid portrait result:", result);
        stats.totalChecked++;
        continue;
      }

      stats.totalChecked++;
      stats.totalFailed++;
      portraitsToDelete.push(portrait);

      // Track primary portraits
      if (portrait.is_primary === true) {
        stats.primaryPortraitsFailed++;
      }

      // Store first 20 failed URLs for dry-run display
      if (stats.failedUrls.length < 20) {
        stats.failedUrls.push(portrait.image_url);
      }

      // Log error details
      const errorMsg = `Portrait ${portrait.id} (member ${
        portrait.member_id
      }): ${checkResult.error || `HTTP ${checkResult.statusCode}`}`;
      stats.errors.push(errorMsg);

      if (stats.totalFailed <= 20) {
        console.log(
          `  ✗ Failed: ${portrait.image_url.substring(0, 80)}... (${
            checkResult.error || `HTTP ${checkResult.statusCode}`
          })`,
        );
      }
    } else {
      stats.totalChecked++;
    }
  }

  console.log(`\n${"=".repeat(80)}`);
  console.log("SUMMARY");
  console.log("=".repeat(80));
  console.log(`Total portraits checked: ${stats.totalChecked}`);
  console.log(`Total portraits with invalid URLs: ${stats.totalFailed}`);
  console.log(
    `Primary portraits with invalid URLs: ${stats.primaryPortraitsFailed}`,
  );
  console.log("");

  // Dry run mode: just show what would be deleted
  if (isDryRun) {
    console.log("DRY RUN MODE - No deletions performed");
    console.log("");
    console.log(`Would soft delete ${portraitsToDelete.length} portraits`);
    console.log(
      `Primary portraits that would be soft deleted: ${stats.primaryPortraitsFailed}`,
    );
    console.log("");
    console.log("First 20 example URLs that would be deleted:");
    stats.failedUrls.forEach((url, index) => {
      console.log(`  ${index + 1}. ${url}`);
    });
    if (stats.failedUrls.length < stats.totalFailed) {
      console.log(
        `  ... and ${stats.totalFailed - stats.failedUrls.length} more`,
      );
    }
  } else {
    // Production mode: actually soft delete in batches
    console.log("PRODUCTION MODE - Soft deleting invalid portraits...");
    console.log("");

    // Filter out any invalid portraits before deletion
    const validPortraitsToDelete = portraitsToDelete.filter(
      (p) => p && p.id && typeof p.id === "string",
    );

    if (validPortraitsToDelete.length !== portraitsToDelete.length) {
      console.log(
        `  Warning: Filtered out ${
          portraitsToDelete.length - validPortraitsToDelete.length
        } invalid portraits`,
      );
    }

    // Process deletions in batches
    for (let i = 0; i < validPortraitsToDelete.length; i += DELETE_BATCH_SIZE) {
      const batch = validPortraitsToDelete.slice(i, i + DELETE_BATCH_SIZE);
      const portraitIds = batch.map((p) => p.id).filter((id) => id); // Filter out any undefined IDs

      if (portraitIds.length === 0) {
        console.log(
          `  Warning: Batch ${
            Math.floor(i / DELETE_BATCH_SIZE) + 1
          } has no valid IDs, skipping`,
        );
        continue;
      }

      const deletedCount = await softDeletePortraitsBatch(portraitIds);
      stats.totalDeleted += deletedCount;

      // Count primary portraits in this batch
      const primaryInBatch = batch.filter((p) => p.is_primary === true).length;
      stats.primaryPortraitsDeleted += primaryInBatch;

      if (
        (i + DELETE_BATCH_SIZE) % 500 === 0 ||
        i + DELETE_BATCH_SIZE >= validPortraitsToDelete.length
      ) {
        console.log(
          `  Deleted ${Math.min(
            i + DELETE_BATCH_SIZE,
            validPortraitsToDelete.length,
          )}/${validPortraitsToDelete.length} portraits...`,
        );
      }
    }

    console.log("");
    console.log(`Successfully soft deleted ${stats.totalDeleted} portraits`);
    console.log(
      `Primary portraits soft deleted: ${stats.primaryPortraitsDeleted}`,
    );
  }

  console.log("");
  console.log("Script completed!");
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
}
