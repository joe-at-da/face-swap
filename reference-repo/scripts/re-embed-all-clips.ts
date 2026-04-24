/**
 * Re-embed all parliament_member_clips with the current embedding model.
 * Uses batch embedding (embedMany) for ~50-100x speedup over sequential.
 *
 * Usage:
 *   npx tsx scripts/re-embed-all-clips.ts
 *   npx tsx scripts/re-embed-all-clips.ts --offset 500   # resume from clip 500
 */

import "dotenv/config";
import { createClient } from "@supabase/supabase-js";
import { generateBatchEmbeddings } from "@/services/ai/embedding-service";

const supabaseUrl =
  process.env.SUPABASE_URL ||
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  "";
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY || "";

if (!supabaseUrl || !supabaseServiceKey) {
  console.error(
    "Error: SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) and SUPABASE_SERVICE_KEY are required"
  );
  process.exit(1);
}

if (!process.env.OPENAI_API_KEY) {
  console.error("Error: OPENAI_API_KEY is required");
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey, {
  auth: { autoRefreshToken: false, persistSession: false },
});

// Tuning constants
const DB_BATCH_SIZE = 200; // clips per DB fetch
const EMBED_BATCH_SIZE = 100; // texts per embedMany call
const MAX_PARALLEL_CALLS = 10; // concurrent OpenAI requests within embedMany
const CONCURRENT_WORKERS = 3; // parallel batch processors
const DELAY_BETWEEN_DB_BATCHES_MS = 100;
const MAX_RETRIES = 3;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseOffset(): number {
  const idx = process.argv.indexOf("--offset");
  if (idx !== -1 && process.argv[idx + 1]) {
    const val = parseInt(process.argv[idx + 1], 10);
    if (!isNaN(val) && val >= 0) return val;
  }
  return 0;
}

interface ClipRow {
  id: string;
  transcript: string | null;
  description: string | null;
}

/**
 * Embed a batch of texts in chunks of EMBED_BATCH_SIZE.
 * Returns formatted pgvector strings in the same order as input.
 */
async function embedTextsInBatches(texts: string[]): Promise<(string | null)[]> {
  const results: (string | null)[] = new Array(texts.length).fill(null);

  for (let i = 0; i < texts.length; i += EMBED_BATCH_SIZE) {
    const chunk = texts.slice(i, i + EMBED_BATCH_SIZE);
    let retries = 0;
    let success = false;

    while (retries < MAX_RETRIES && !success) {
      const result = await generateBatchEmbeddings(chunk, MAX_PARALLEL_CALLS);

      if (result.data) {
        for (let j = 0; j < result.data.length; j++) {
          results[i + j] = result.data[j];
        }
        success = true;
      } else {
        retries++;
        if (retries < MAX_RETRIES) {
          const wait = 2000 * retries;
          console.warn(
            `  Embed batch retry ${retries}/${MAX_RETRIES} (texts ${i}-${i + chunk.length - 1}): ${result.error}. Waiting ${wait}ms...`
          );
          await sleep(wait);
        } else {
          console.error(
            `  Embed batch FAILED (texts ${i}-${i + chunk.length - 1}): ${result.error}`
          );
        }
      }
    }
  }

  return results;
}

/**
 * Process a single batch: fetch → embed → update DB.
 * Returns stats for this batch.
 */
async function processBatch(
  batchOffset: number,
): Promise<{ processed: number; errors: number; clipCount: number }> {
  const { data: clips, error: fetchError } = await supabase
    .from("parliament_member_clips")
    .select("id, transcript, description")
    .eq("is_deleted", false)
    .not("transcript", "is", null)
    .neq("transcript", "")
    .order("id")
    .range(batchOffset, batchOffset + DB_BATCH_SIZE - 1);

  if (fetchError) {
    console.error(`[offset ${batchOffset}] Fetch failed:`, fetchError.message);
    return { processed: 0, errors: 0, clipCount: 0 };
  }

  if (!clips || clips.length === 0) {
    return { processed: 0, errors: 0, clipCount: 0 };
  }

  // Collect all texts with index mapping
  const textEntries: { clipIdx: number; field: "transcript" | "description"; text: string }[] = [];

  for (let i = 0; i < clips.length; i++) {
    const clip = clips[i] as ClipRow;
    if (clip.transcript) {
      textEntries.push({ clipIdx: i, field: "transcript", text: clip.transcript });
    }
    if (clip.description) {
      textEntries.push({ clipIdx: i, field: "description", text: clip.description });
    }
  }

  // Batch embed all texts
  const allTexts = textEntries.map((e) => e.text);
  const embeddings = await embedTextsInBatches(allTexts);

  // Map embeddings back to clips and build updates
  const updates: { id: string; transcript_embedding?: string; description_embedding?: string }[] = [];

  for (let i = 0; i < textEntries.length; i++) {
    const entry = textEntries[i];
    const embedding = embeddings[i];
    if (!embedding) continue;

    const clip = clips[entry.clipIdx] as ClipRow;
    let existing = updates.find((u) => u.id === clip.id);
    if (!existing) {
      existing = { id: clip.id };
      updates.push(existing);
    }

    if (entry.field === "transcript") {
      existing.transcript_embedding = embedding;
    } else {
      existing.description_embedding = embedding;
    }
  }

  // Batch DB updates (parallel, 20 at a time)
  let batchErrors = 0;
  for (let i = 0; i < updates.length; i += 20) {
    const chunk = updates.slice(i, i + 20);
    const results = await Promise.allSettled(
      chunk.map((update) => {
        const { id, ...fields } = update;
        return supabase
          .from("parliament_member_clips")
          .update(fields)
          .eq("id", id);
      })
    );

    for (const result of results) {
      if (result.status === "rejected" || (result.status === "fulfilled" && result.value.error)) {
        batchErrors++;
      }
    }
  }

  return { processed: updates.length, errors: batchErrors, clipCount: clips.length };
}

async function main() {
  const startOffset = parseOffset();
  console.log("=== Re-embedding clips with text-embedding-3-large (batch mode) ===");
  console.log(`Workers: ${CONCURRENT_WORKERS} | Batch: ${DB_BATCH_SIZE} | Embed chunk: ${EMBED_BATCH_SIZE} | Parallel calls: ${MAX_PARALLEL_CALLS}\n`);

  // Count total
  const { count: totalCount, error: countError } = await supabase
    .from("parliament_member_clips")
    .select("id", { count: "exact", head: true })
    .eq("is_deleted", false)
    .not("transcript", "is", null)
    .neq("transcript", "");

  if (countError) {
    console.error("Failed to count clips:", countError.message);
    process.exit(1);
  }

  const total = totalCount || 0;
  console.log(`Total clips: ${total}`);
  if (startOffset > 0) console.log(`Resuming from offset: ${startOffset}`);

  if (total === 0) {
    console.log("Nothing to do.");
    return;
  }

  // Build offset queue
  const offsets: number[] = [];
  for (let o = startOffset; o < total; o += DB_BATCH_SIZE) {
    offsets.push(o);
  }

  let nextIdx = 0; // shared index into offsets array
  let totalProcessed = 0;
  let totalErrors = 0;
  let totalClips = 0;
  const startTime = Date.now();

  // Worker: grab next offset from queue, process, repeat
  async function worker(workerId: number) {
    while (true) {
      const idx = nextIdx++;
      if (idx >= offsets.length) break;

      const batchOffset = offsets[idx];
      const batchStart = Date.now();

      const result = await processBatch(batchOffset);

      totalProcessed += result.processed;
      totalErrors += result.errors;
      totalClips += result.clipCount;

      const elapsed = (Date.now() - startTime) / 1000;
      const rate = totalClips / elapsed;
      const remaining = total - startOffset - totalClips;
      const eta = rate > 0 ? Math.ceil(remaining / rate) : 0;
      const batchTime = ((Date.now() - batchStart) / 1000).toFixed(1);

      console.log(
        `[W${workerId}] ${totalClips + startOffset}/${total} | ${result.processed} updated (${result.errors} err) | ${batchTime}s | ${rate.toFixed(1)} clips/s | ETA: ${eta}s`
      );

      if (idx < offsets.length - 1) {
        await sleep(DELAY_BETWEEN_DB_BATCHES_MS);
      }
    }
  }

  // Launch workers
  const workers = Array.from({ length: CONCURRENT_WORKERS }, (_, i) => worker(i + 1));
  await Promise.all(workers);

  const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`\n=== Complete in ${totalTime}s ===`);
  console.log(`Processed: ${totalProcessed} | Errors: ${totalErrors}`);
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
