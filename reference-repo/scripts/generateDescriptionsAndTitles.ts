import { generateAndFormatEmbedding } from "@/services/ai/embedding-service";
import {
  generateClipDescription,
  generateClipTitle,
} from "@/services/ai/generation-service";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

const TESTING = false;

// Configuration for batch processing
// Tier 3 OpenAI limits: 5,000 RPM, 4M TPM
// Each clip makes 2-4 API calls (description/title + embeddings)
// With 75 concurrent clips: ~150-300 concurrent API calls
// At ~1-2s per call: ~75-150 req/s = 4,500-9,000 req/min (safe margin under 5,000 RPM)
const CONCURRENCY_LIMIT = 75; // Number of clips to process in parallel (optimized for Tier 3 limits)
const RETRY_MAX_ATTEMPTS = 5; // Max retries for retryable errors
const RETRY_DELAY_MS = 2000; // Initial delay for retries (exponential backoff)
const SUPABASE_RETRY_MAX_ATTEMPTS = 3; // Max retries for Supabase operations
const UPDATE_BATCH_SIZE = 75; // Number of updates to execute in parallel
const SUPABASE_UPDATE_CONCURRENCY = 75; // Number of Supabase updates to execute concurrently

/**
 * Sleep utility function
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Serialize error to string for logging
 */
function serializeError(error: unknown): string {
  if (error instanceof Error) {
    // Standard Error object
    const errorObj: Record<string, unknown> = {
      message: error.message,
      name: error.name,
    };
    if (error.stack) {
      errorObj.stack = error.stack;
    }
    // Add any additional properties
    if (error.cause) {
      errorObj.cause = error.cause;
    }
    return JSON.stringify(errorObj, null, 2);
  } else if (error && typeof error === "object") {
    // PostgREST errors or other object errors
    const err = error as Record<string, unknown>;
    // Try to extract common Supabase/PostgREST error properties
    const errorObj: Record<string, unknown> = {};
    if (err.message) errorObj.message = err.message;
    if (err.details) errorObj.details = err.details;
    if (err.hint) errorObj.hint = err.hint;
    if (err.code) errorObj.code = err.code;
    if (err.status) errorObj.status = err.status;
    if (err.statusCode) errorObj.statusCode = err.statusCode;
    // Include all other properties
    Object.keys(err).forEach((key) => {
      if (!errorObj[key]) {
        errorObj[key] = err[key];
      }
    });
    return JSON.stringify(errorObj, null, 2);
  } else {
    // Primitive types
    return String(error);
  }
}

/**
 * Check if error is retryable (rate limit, service unavailable, network errors)
 */
function isRetryableError(error: unknown): boolean {
  if (!error || typeof error !== "object") {
    return false;
  }

  const err = error as Record<string, unknown>;
  const errorMessage = String(err.message || "").toLowerCase();
  const errorDetails = String(err.details || "").toLowerCase();

  // Check status property for HTTP errors
  if (typeof err.status === "number") {
    // 429 = Rate limit, 503 = Service Unavailable, 502 = Bad Gateway, 504 = Gateway Timeout
    if ([429, 503, 502, 504].includes(err.status)) {
      return true;
    }
  }

  // Check statusCode property
  if (typeof err.statusCode === "number") {
    if ([429, 503, 502, 504].includes(err.statusCode)) {
      return true;
    }
  }

  // Check response.status property
  if (err.response && typeof err.response === "object") {
    const response = err.response as Record<string, unknown>;
    if (
      typeof response.status === "number" &&
      [429, 503, 502, 504].includes(response.status)
    ) {
      return true;
    }
  }

  // Check for network errors
  if (
    errorMessage.includes("fetch failed") ||
    errorMessage.includes("network") ||
    errorMessage.includes("connection") ||
    errorMessage.includes("timeout") ||
    errorMessage.includes("econnrefused") ||
    errorMessage.includes("service unavailable") ||
    errorDetails.includes("fetch failed") ||
    errorDetails.includes("connection refused") ||
    errorDetails.includes("remote connection failure")
  ) {
    return true;
  }

  // Check for rate limit in message
  if (errorMessage.includes("rate limit")) {
    return true;
  }

  return false;
}

/**
 * Retry wrapper for API calls with exponential backoff
 */
async function retryOnError<T>(
  fn: () => Promise<T>,
  attempt = 1,
  maxAttempts = RETRY_MAX_ATTEMPTS,
  operationName = "operation"
): Promise<T> {
  try {
    return await fn();
  } catch (error: unknown) {
    if (isRetryableError(error) && attempt < maxAttempts) {
      const delay = RETRY_DELAY_MS * Math.pow(2, attempt - 1);
      const errorMsg = serializeError(error);
      // Truncate to first 500 chars for readability, but log full error
      const truncatedMsg =
        errorMsg.length > 500 ? errorMsg.substring(0, 500) + "..." : errorMsg;
      console.log(
        `[${operationName}] Retryable error (attempt ${attempt}/${
          maxAttempts - 1
        }): ${truncatedMsg}. Retrying in ${delay}ms...`
      );
      await sleep(delay);
      return retryOnError(fn, attempt + 1, maxAttempts, operationName);
    }
    throw error;
  }
}

/**
 * Update data type for batch updates
 */
type UpdateData = {
  id: string;
  table: "parliament_member_clips" | "user_clips";
  data: Record<string, unknown>;
};

/**
 * Process a single parliament member clip
 */
type ParliamentMemberClipWithMember = {
  id: string;
  transcript: string;
  parliament_members: {
    display_name: string | null;
    constituency_name: string | null;
    party_abbreviation: string | null;
  };
  [key: string]: unknown;
};
type ParliamentMemberClipResult = {
  type: "parliament_member_clip";
  clip_id: string;
  clip_url: unknown;
  description: string;
  description_embedding: unknown;
  update: UpdateData;
};

async function processParliamentMemberClip(
  clip: ParliamentMemberClipWithMember
): Promise<ParliamentMemberClipResult | null> {
  try {
    const descriptionResult = await retryOnError(
      () =>
        generateClipDescription(clip.transcript, {
          display_name: clip.parliament_members.display_name || null,
          constituency_name: clip.parliament_members.constituency_name || null,
          party_abbreviation:
            clip.parliament_members.party_abbreviation || null,
        }),
      1,
      RETRY_MAX_ATTEMPTS,
      `generateDescription-${clip.id}`
    );

    if (!descriptionResult.data) {
      console.error(
        `Error generating description for clip ${clip.id}:`,
        serializeError(descriptionResult.error)
      );
      return null;
    }

    const description = descriptionResult.data;

    const descriptionEmbeddingResult = await retryOnError(
      () => generateAndFormatEmbedding(description),
      1,
      RETRY_MAX_ATTEMPTS,
      `generateEmbedding-${clip.id}`
    );

    if (descriptionEmbeddingResult.error) {
      console.error(
        `Error generating description embedding for clip ${clip.id}:`,
        serializeError(descriptionEmbeddingResult.error)
      );
      return null;
    }

    return {
      type: "parliament_member_clip",
      clip_id: clip.id,
      clip_url: clip.clip_url,
      description: description,
      description_embedding: descriptionEmbeddingResult,
      update: {
        id: clip.id,
        table: "parliament_member_clips",
        data: {
          description: description,
          description_embedding: descriptionEmbeddingResult.data,
        },
      },
    };
  } catch (error) {
    console.error(
      `Error processing parliament member clip ${clip.id}:`,
      serializeError(error)
    );
    return null;
  }
}

/**
 * Batch update helper for Supabase operations
 */
async function batchUpdateSupabase(
  updates: UpdateData[],
  batchSize: number = UPDATE_BATCH_SIZE
): Promise<{ successful: number; failed: number }> {
  if (updates.length === 0) {
    return { successful: 0, failed: 0 };
  }

  let successful = 0;
  let failed = 0;

  // Group updates by table
  const updatesByTable = updates.reduce((acc, update) => {
    if (!acc[update.table]) {
      acc[update.table] = [];
    }
    acc[update.table].push(update);
    return acc;
  }, {} as Record<string, UpdateData[]>);

  // Process each table's updates in batches
  for (const [table, tableUpdates] of Object.entries(updatesByTable)) {
    console.log(`Batch updating ${tableUpdates.length} records in ${table}...`);

    for (let i = 0; i < tableUpdates.length; i += batchSize) {
      const batch = tableUpdates.slice(i, i + batchSize);
      const batchNumber = Math.floor(i / batchSize) + 1;
      const totalBatches = Math.ceil(tableUpdates.length / batchSize);

      console.log(
        `  Processing update batch ${batchNumber}/${totalBatches} (${batch.length} updates)`
      );

      // Process updates in smaller concurrent groups to avoid overwhelming the database
      const results: Array<{ success: boolean; id: string }> = [];
      for (let j = 0; j < batch.length; j += SUPABASE_UPDATE_CONCURRENCY) {
        const concurrentGroup = batch.slice(j, j + SUPABASE_UPDATE_CONCURRENCY);

        const updatePromises = concurrentGroup.map(async (update) => {
          try {
            await retryOnError(
              async () => {
                const dbResult = await supabaseAdminClient
                  .from(update.table)
                  .update(update.data)
                  .eq("id", update.id);
                if (dbResult.error) {
                  throw dbResult.error;
                }
                return dbResult;
              },
              1,
              SUPABASE_RETRY_MAX_ATTEMPTS,
              `batchUpdate-${update.table}-${update.id}`
            );
            return { success: true, id: update.id };
          } catch (error) {
            console.error(
              `Failed to update ${update.table} record ${update.id}:`,
              serializeError(error)
            );
            return { success: false, id: update.id };
          }
        });

        const groupResults = await Promise.all(updatePromises);
        results.push(...groupResults);

        // Small delay between concurrent groups to avoid overwhelming the database
        if (j + SUPABASE_UPDATE_CONCURRENCY < batch.length) {
          await sleep(50);
        }
      }
      const batchSuccessful = results.filter((r) => r.success).length;
      const batchFailed = results.length - batchSuccessful;
      successful += batchSuccessful;
      failed += batchFailed;

      console.log(
        `  Completed update batch ${batchNumber}/${totalBatches}: ${batchSuccessful}/${batch.length} successful`
      );

      // Small delay between batches to avoid overwhelming the database
      if (i + batchSize < tableUpdates.length) {
        await sleep(100);
      }
    }
  }

  console.log(
    `Batch updates complete: ${successful} successful, ${failed} failed`
  );
  return { successful, failed };
}

/**
 * Process clips in batches with concurrency limit
 * @param onBatchComplete Optional callback called after each batch with results. Should return a promise that resolves when updates are done.
 */
async function processBatch<T, R>(
  items: T[],
  processor: (item: T) => Promise<R | null>,
  batchSize: number,
  type: string,
  onBatchComplete?: (batchResults: R[], batchNumber: number) => Promise<void>
): Promise<R[]> {
  const results: R[] = [];
  const total = items.length;
  const BATCH_DELAY_MS = 500; // Delay between batches to avoid overwhelming the API

  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    const batchNumber = Math.floor(i / batchSize) + 1;
    const totalBatches = Math.ceil(total / batchSize);

    console.log(
      `Processing ${type} batch ${batchNumber}/${totalBatches} (${
        batch.length
      } items, ${i + 1}-${Math.min(i + batchSize, total)}/${total})`
    );

    const batchResults = await Promise.all(
      batch.map((item) => processor(item))
    );

    const successful = batchResults.filter((r) => r !== null) as R[];
    results.push(...successful);

    console.log(
      `Completed ${type} batch ${batchNumber}/${totalBatches}: ${successful.length}/${batch.length} successful`
    );

    // If there's a callback and more batches to process, handle updates with timing
    if (onBatchComplete && i + batchSize < items.length) {
      const updateStartTime = Date.now();

      // Start the update process and ensure errors are handled
      const updatePromise = onBatchComplete(successful, batchNumber).catch(
        (error) => {
          console.error(
            `Error in batch update callback for batch ${batchNumber}:`,
            serializeError(error)
          );
        }
      );

      // Wait for either updates to complete OR the delay time, whichever comes first
      const raceResult = await Promise.race([
        updatePromise.then(() => ({ completed: true })),
        sleep(BATCH_DELAY_MS).then(() => ({ completed: false })),
      ]);

      // Calculate elapsed time
      const elapsedTime = Date.now() - updateStartTime;

      if (raceResult.completed) {
        // Updates completed - wait for remaining delay time if needed
        const remainingDelay = Math.max(0, BATCH_DELAY_MS - elapsedTime);
        if (remainingDelay > 0) {
          await sleep(remainingDelay);
        }
      } else {
        // Delay passed but updates may still be running - wait a bit more for them
        // to reduce concurrent Supabase operations. We'll wait up to another delay period
        // to give updates time to complete, but then proceed to avoid blocking too long
        const additionalWait = BATCH_DELAY_MS; // Wait another full delay period
        await Promise.race([updatePromise, sleep(additionalWait)]);
      }
    } else if (onBatchComplete && i + batchSize >= items.length) {
      // Last batch - wait for updates to complete
      await onBatchComplete(successful, batchNumber);
    } else if (i + batchSize < items.length) {
      // No callback, use simple delay
      await sleep(BATCH_DELAY_MS);
    }
  }

  return results;
}

export async function generateDescriptionsAndTitles() {
  console.log("Generating descriptions and titles");
  const allParliamentMemberClips = [];
  let page = 1;
  const pageSize = 1000;
  let hasMore = true;

  console.log("Fetching parliament member clips...");
  while (hasMore) {
    const startRange = (page - 1) * pageSize;
    const endRange = page * pageSize - 1;
    console.log(`  Fetching page ${page} (range ${startRange}-${endRange})...`);

    const queryStartTime = Date.now();
    const { data, error } = await retryOnError(
      async () => {
        const result = await supabaseAdminClient
          .from("parliament_member_clips")
          .select(
            "*, parliament_members(display_name, constituency_name, party_abbreviation)"
          )
          .not("transcript", "is", null)
          .is("description", null)
          .range(startRange, endRange);
        if (result.error) {
          throw result.error;
        }
        return result;
      },
      1,
      SUPABASE_RETRY_MAX_ATTEMPTS,
      `fetchParliamentClips-page${page}`
    );
    const queryDuration = Date.now() - queryStartTime;
    console.log(`  Query completed in ${queryDuration}ms`);

    if (error) {
      console.error(
        "Error fetching all parliament member clips:",
        serializeError(error)
      );
      return;
    }

    if (data && data.length > 0) {
      allParliamentMemberClips.push(...data);
      console.log(
        `  Page ${page}: Fetched ${data.length} clips (total: ${allParliamentMemberClips.length})`
      );
      page++;
      hasMore = data.length === pageSize;
    } else {
      console.log(`  Page ${page}: No more data`);
      hasMore = false;
    }
  }

  console.log(
    `Found ${allParliamentMemberClips?.length} parliament member clips`
  );

  const results = [];

  if (TESTING && allParliamentMemberClips.length > 0) {
    // Process only first clip in testing mode
    const result = await processParliamentMemberClip(
      allParliamentMemberClips[0]
    );
    if (result) {
      results.push(result);
      // Update immediately in testing mode
      await batchUpdateSupabase([result.update], UPDATE_BATCH_SIZE);
    }
  } else {
    // Process all clips in parallel batches with interleaved Supabase updates
    const parliamentResults = await processBatch(
      allParliamentMemberClips,
      processParliamentMemberClip,
      CONCURRENCY_LIMIT,
      "parliament_member_clips",
      async (batchResults, batchNumber) => {
        // Extract updates from this batch
        const batchUpdates = batchResults.map((r) => r.update).filter(Boolean);

        if (batchUpdates.length > 0) {
          console.log(
            `Updating Supabase for parliament_member_clips batch ${batchNumber} (${batchUpdates.length} updates)...`
          );
          await batchUpdateSupabase(batchUpdates, UPDATE_BATCH_SIZE);
        }
      }
    );
    results.push(...parliamentResults);
  }

  const allUserClips = [];
  page = 1;
  hasMore = true;
  console.log("Fetching user clips...");
  while (hasMore) {
    const startRange = (page - 1) * pageSize;
    const endRange = page * pageSize - 1;
    console.log(`  Fetching page ${page} (range ${startRange}-${endRange})...`);

    const queryStartTime = Date.now();
    const { data, error } = await retryOnError(
      async () => {
        const result = await supabaseAdminClient
          .from("user_clips")
          .select(
            `*,
             parliament_member_clips(parliament_members(display_name, constituency_name, party_abbreviation))`
          )
          .not("transcript", "is", null)
          .range(startRange, endRange);
        if (result.error) {
          throw result.error;
        }
        return result;
      },
      1,
      SUPABASE_RETRY_MAX_ATTEMPTS,
      `fetchUserClips-page${page}`
    );
    const queryDuration = Date.now() - queryStartTime;
    console.log(`  Query completed in ${queryDuration}ms`);

    if (error) {
      console.error("Error fetching all user clips:", serializeError(error));
      return;
    }

    if (data && data.length > 0) {
      allUserClips.push(...data);
      console.log(
        `  Page ${page}: Fetched ${data.length} clips (total: ${allUserClips.length})`
      );
      page++;
      hasMore = data.length === pageSize;
    } else {
      console.log(`  Page ${page}: No more data`);
      hasMore = false;
    }
  }

  console.log(`Found ${allUserClips?.length} user clips`);

  /**
   * Process a single user clip
   */
  type UserClip = {
    id: string;
    transcript: string | null;
    parliament_member_clips: {
      parliament_members: {
        display_name: string | null;
        constituency_name: string | null;
        party_abbreviation: string | null;
      };
    };
    [key: string]: unknown;
  };
  type UserClipResult = {
    type: "user_clip";
    clip_id: string;
    clip_url: unknown;
    description: string;
    description_embedding: unknown;
    title: string;
    title_embedding: unknown;
    update: UpdateData;
  };

  async function processUserClip(
    clip: UserClip
  ): Promise<UserClipResult | null> {
    try {
      if (!clip.transcript) {
        console.error(`Error: Clip ${clip.id} has no transcript`);
        return null;
      }

      const transcript = clip.transcript;
      const descriptionResult = await retryOnError(
        () =>
          generateClipDescription(transcript, {
            display_name:
              clip.parliament_member_clips.parliament_members.display_name ||
              null,
            constituency_name:
              clip.parliament_member_clips.parliament_members
                .constituency_name || null,
            party_abbreviation:
              clip.parliament_member_clips.parliament_members
                .party_abbreviation || null,
          }),
        1,
        RETRY_MAX_ATTEMPTS,
        `generateDescription-${clip.id}`
      );

      if (!descriptionResult.data) {
        console.error(
          `Error generating description for clip ${clip.id}:`,
          serializeError(descriptionResult.error)
        );
        return null;
      }

      const description = descriptionResult.data;

      const descriptionEmbeddingResult = await retryOnError(
        () => generateAndFormatEmbedding(description),
        1,
        RETRY_MAX_ATTEMPTS,
        `generateDescriptionEmbedding-${clip.id}`
      );

      if (descriptionEmbeddingResult.error) {
        console.error(
          `Error generating description embedding for clip ${clip.id}:`,
          serializeError(descriptionEmbeddingResult.error)
        );
        return null;
      }

      const titleResult = await retryOnError(
        () =>
          generateClipTitle(transcript, {
            display_name:
              clip.parliament_member_clips.parliament_members.display_name ||
              null,
            party_abbreviation:
              clip.parliament_member_clips.parliament_members
                .party_abbreviation || null,
            constituency_name:
              clip.parliament_member_clips.parliament_members
                .constituency_name || null,
          }),
        1,
        RETRY_MAX_ATTEMPTS,
        `generateTitle-${clip.id}`
      );

      if (!titleResult.data) {
        console.error(
          `Error generating title for clip ${clip.id}:`,
          serializeError(titleResult.error)
        );
        return null;
      }

      const title = titleResult.data;

      const titleEmbeddingResult = await retryOnError(
        () => generateAndFormatEmbedding(title),
        1,
        RETRY_MAX_ATTEMPTS,
        `generateTitleEmbedding-${clip.id}`
      );

      if (titleEmbeddingResult.error) {
        console.error(
          `Error generating title embedding for clip ${clip.id}:`,
          serializeError(titleEmbeddingResult.error)
        );
        return null;
      }

      return {
        type: "user_clip",
        clip_id: clip.id,
        clip_url: clip.clip_url,
        description: description,
        description_embedding: descriptionEmbeddingResult,
        title: title,
        title_embedding: titleEmbeddingResult,
        update: {
          id: clip.id,
          table: "user_clips",
          data: {
            description: description,
            description_embedding: descriptionEmbeddingResult.data,
            title: title,
            title_embedding: titleEmbeddingResult.data,
          },
        },
      };
    } catch (error) {
      console.error(
        `Error processing user clip ${clip.id}:`,
        serializeError(error)
      );
      return null;
    }
  }

  const userUpdates: UpdateData[] = [];

  if (TESTING && allUserClips.length > 0) {
    // Process only first clip in testing mode
    const result = await processUserClip(allUserClips[0]);
    if (result) {
      results.push(result);
      userUpdates.push(result.update);
    }
  } else {
    // Process all clips in parallel batches
    const userResults = await processBatch(
      allUserClips,
      processUserClip,
      CONCURRENCY_LIMIT,
      "user_clips"
    );
    results.push(...userResults);
    userUpdates.push(...userResults.map((r) => r.update).filter(Boolean));
  }

  // Batch update all user clips
  if (userUpdates.length > 0) {
    console.log(`\nBatch updating ${userUpdates.length} user clips...`);
    await batchUpdateSupabase(userUpdates, UPDATE_BATCH_SIZE);
  }

  console.log(
    `\nProcessing complete! Total results: ${results.length} (${
      results.filter((r) => r.type === "parliament_member_clip").length
    } parliament member clips, ${
      results.filter((r) => r.type === "user_clip").length
    } user clips)`
  );

  return results;
}
