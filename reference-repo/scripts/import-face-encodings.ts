import { createClient } from "@supabase/supabase-js";
import { Database, Json } from "../supabaseTypes";
import * as fs from "fs";
import * as path from "path";
import * as dotenv from "dotenv";
import * as readline from "readline";

// Load environment variables
dotenv.config({ path: path.join(__dirname, "..", ".env") });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
  console.error("Missing environment variables:");
  console.error("- NEXT_PUBLIC_SUPABASE_URL:", supabaseUrl ? "set" : "missing");
  console.error(
    "- SUPABASE_SERVICE_KEY:",
    supabaseServiceKey ? "set" : "missing",
  );
  process.exit(1);
}

const supabase = createClient<Database>(supabaseUrl, supabaseServiceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});

type FaceEncodingInsert =
  Database["public"]["Tables"]["parliament_member_face_encodings"]["Insert"];

// Parse CSV line handling quoted fields
function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else if (char !== "\r" && char !== "\n") {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}

function parseNumber(value: string): number | null {
  if (!value || value === "") return null;
  const num = parseFloat(value);
  return isNaN(num) ? null : num;
}

function parseBoolean(value: string): boolean | null {
  if (!value || value === "") return null;
  return value === "true";
}

function parseJson(value: string): Json | null {
  if (!value || value === "") return null;
  try {
    return JSON.parse(value) as Json;
  } catch {
    return null;
  }
}

async function importFaceEncodings() {
  const csvPath = path.join(
    __dirname,
    "..",
    "backups",
    "parliament_member_face_encodings_rows.csv",
  );

  console.log("=== Importing Parliament Member Face Encodings ===");
  console.log(`Supabase URL: ${supabaseUrl}`);
  console.log(`CSV File: ${csvPath}`);

  if (!fs.existsSync(csvPath)) {
    console.error(`Error: CSV file not found at ${csvPath}`);
    process.exit(1);
  }

  const stats = fs.statSync(csvPath);
  console.log(`File size: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);

  // Check current counts
  const { count: currentCount } = await supabase
    .from("parliament_member_face_encodings")
    .select("*", { count: "exact", head: true });

  const { count: portraitCount } = await supabase
    .from("parliament_member_portraits")
    .select("*", { count: "exact", head: true });

  console.log(`\nCurrent face encodings in database: ${currentCount}`);
  console.log(`Portrait dependencies available: ${portraitCount}`);

  if (portraitCount === 0) {
    console.error(
      "\nError: No portraits found. Run import-portraits.ts first!",
    );
    process.exit(1);
  }

  // Get all existing portrait_ids to filter face encodings (paginate to get all)
  console.log("Fetching existing portrait IDs...");
  const validPortraitIds = new Set<string>();
  let page = 0;
  const pageSize = 1000;

  while (true) {
    const { data: existingPortraits, error: portraitsError } = await supabase
      .from("parliament_member_portraits")
      .select("id")
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (portraitsError) {
      console.error("Error fetching portraits:", portraitsError.message);
      process.exit(1);
    }

    if (!existingPortraits || existingPortraits.length === 0) break;

    for (const p of existingPortraits) {
      validPortraitIds.add(p.id);
    }

    process.stdout.write(`\rFetched ${validPortraitIds.size} portrait IDs...`);

    if (existingPortraits.length < pageSize) break;
    page++;
  }

  console.log(`\nFound ${validPortraitIds.size} existing portraits`);

  // Stream read the file line by line for memory efficiency
  const fileStream = fs.createReadStream(csvPath);
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  let lineNumber = 0;
  let headers: string[] = [];
  const BATCH_SIZE = 100; // Smaller batch due to large face_encoding data
  let batchMap = new Map<string, FaceEncodingInsert>(); // Deduplicate by ID within batch
  let inserted = 0;
  let errors = 0;
  let skipped = 0;
  let skippedNoPortrait = 0;
  let duplicatesRemoved = 0;
  const failedRecords: Array<{ record: FaceEncodingInsert; error: string }> =
    [];
  const seenIds = new Set<string>(); // Track all seen IDs globally
  const missingPortraitIds = new Set<string>(); // Track which portrait_ids are missing

  console.log("\nProcessing CSV...");

  for await (const line of rl) {
    lineNumber++;

    if (lineNumber === 1) {
      headers = parseCSVLine(line);
      console.log(
        `Headers: ${headers.slice(0, 5).join(", ")}... (${
          headers.length
        } columns)`,
      );
      continue;
    }

    if (!line.trim()) continue;

    const fields = parseCSVLine(line);
    if (fields.length < 20) {
      skipped++;
      continue;
    }

    // CSV columns based on header:
    // id,member_id,portrait_id,face_encoding,face_encoding_json,detection_confidence,
    // encoding_quality,face_bbox_top,face_bbox_right,face_bbox_bottom,face_bbox_left,
    // image_width,image_height,processing_model,processing_date,processing_version,
    // is_primary_encoding,is_validated,is_active,is_deleted,deleted_at,created_at,
    // updated_at,last_synced_at,processing_notes,error_message
    const [
      id,
      member_id,
      portrait_id,
      face_encoding,
      face_encoding_json,
      detection_confidence,
      encoding_quality,
      face_bbox_top,
      face_bbox_right,
      face_bbox_bottom,
      face_bbox_left,
      image_width,
      image_height,
      processing_model,
      processing_date,
      processing_version,
      is_primary_encoding,
      is_validated,
      is_active,
      is_deleted,
      deleted_at,
      created_at,
      updated_at,
      last_synced_at,
      processing_notes,
      error_message,
    ] = fields;

    // Skip face encodings for portraits that don't exist
    if (!validPortraitIds.has(portrait_id)) {
      skippedNoPortrait++;
      missingPortraitIds.add(portrait_id);
      continue;
    }

    const record: FaceEncodingInsert = {
      id,
      member_id: parseInt(member_id, 10),
      portrait_id,
      face_encoding,
      face_encoding_json: parseJson(face_encoding_json),
      detection_confidence: parseNumber(detection_confidence),
      encoding_quality: parseNumber(encoding_quality),
      face_bbox_top: parseNumber(face_bbox_top),
      face_bbox_right: parseNumber(face_bbox_right),
      face_bbox_bottom: parseNumber(face_bbox_bottom),
      face_bbox_left: parseNumber(face_bbox_left),
      image_width: parseNumber(image_width),
      image_height: parseNumber(image_height),
      processing_model: processing_model || null,
      processing_date: processing_date || null,
      processing_version: processing_version || null,
      is_primary_encoding: parseBoolean(is_primary_encoding),
      is_validated: parseBoolean(is_validated),
      is_active: parseBoolean(is_active),
      is_deleted: is_deleted === "true",
      deleted_at: deleted_at || null,
      created_at: created_at || null,
      updated_at: updated_at || null,
      last_synced_at: last_synced_at || null,
      processing_notes: processing_notes || null,
      error_message: error_message || null,
    };

    // Track duplicates - if ID already seen in this batch, overwrite (keep latest)
    if (seenIds.has(id)) {
      duplicatesRemoved++;
    }
    seenIds.add(id);
    batchMap.set(id, record);

    if (batchMap.size >= BATCH_SIZE) {
      const batch = Array.from(batchMap.values());
      const { error } = await supabase
        .from("parliament_member_face_encodings")
        .upsert(batch, { onConflict: "id" });

      if (error) {
        console.error(`\nError at line ${lineNumber}:`, error.message);
        console.error(`Error code: ${error.code}`);
        console.error(`Error details: ${error.details}`);
        console.error(`Error hint: ${error.hint}`);

        // Try to insert records one by one to identify the problematic ones
        console.log(
          `\nRetrying batch records individually to identify failures...`,
        );
        for (const rec of batch) {
          const { error: singleError } = await supabase
            .from("parliament_member_face_encodings")
            .upsert(rec, { onConflict: "id" });

          if (singleError) {
            errors++;
            failedRecords.push({
              record: rec,
              error: `${singleError.code}: ${singleError.message} - ${singleError.details || ""}`,
            });
            console.error(`\n  Failed record:`);
            console.error(`    ID: ${rec.id}`);
            console.error(`    Member ID: ${rec.member_id}`);
            console.error(`    Portrait ID: ${rec.portrait_id}`);
            console.error(`    Error: ${singleError.message}`);
          } else {
            inserted++;
          }
        }
      } else {
        inserted += batch.length;
      }

      process.stdout.write(
        `\rProcessed: ${
          lineNumber - 1
        } | Inserted: ${inserted} | Errors: ${errors} | Skipped: ${skippedNoPortrait} | Duplicates: ${duplicatesRemoved}`,
      );
      batchMap = new Map();
    }
  }

  // Insert remaining batch
  if (batchMap.size > 0) {
    const batch = Array.from(batchMap.values());
    const { error } = await supabase
      .from("parliament_member_face_encodings")
      .upsert(batch, { onConflict: "id" });

    if (error) {
      console.error(`\nError in final batch:`, error.message);
      console.error(`Error code: ${error.code}`);
      console.error(`Error details: ${error.details}`);
      console.error(`Error hint: ${error.hint}`);

      // Try to insert records one by one to identify the problematic ones
      console.log(
        `\nRetrying final batch records individually to identify failures...`,
      );
      for (const rec of batch) {
        const { error: singleError } = await supabase
          .from("parliament_member_face_encodings")
          .upsert(rec, { onConflict: "id" });

        if (singleError) {
          errors++;
          failedRecords.push({
            record: rec,
            error: `${singleError.code}: ${singleError.message} - ${singleError.details || ""}`,
          });
          console.error(`\n  Failed record:`);
          console.error(`    ID: ${rec.id}`);
          console.error(`    Member ID: ${rec.member_id}`);
          console.error(`    Portrait ID: ${rec.portrait_id}`);
          console.error(`    Error: ${singleError.message}`);
        } else {
          inserted++;
        }
      }
    } else {
      inserted += batch.length;
    }
  }

  console.log("\n");

  // Log all failed records summary
  if (failedRecords.length > 0) {
    console.log(`\n=== Failed Records Summary ===`);
    console.log(`Total failed: ${failedRecords.length}`);

    // Group failures by error type
    const errorGroups = failedRecords.reduce(
      (acc, item) => {
        const key = item.error;
        if (!acc[key]) acc[key] = [];
        acc[key].push(item.record);
        return acc;
      },
      {} as Record<string, FaceEncodingInsert[]>,
    );

    for (const [errorMsg, records] of Object.entries(errorGroups)) {
      console.log(`\nError: ${errorMsg}`);
      console.log(`Count: ${records.length}`);
      console.log(
        `Sample portrait_ids: ${records
          .slice(0, 5)
          .map((r) => r.portrait_id)
          .join(", ")}`,
      );
      console.log(
        `Sample member_ids: ${records
          .slice(0, 5)
          .map((r) => r.member_id)
          .join(", ")}`,
      );
    }
  }

  // Verify final count
  const { count: finalCount } = await supabase
    .from("parliament_member_face_encodings")
    .select("*", { count: "exact", head: true });

  console.log(`\n=== Import Complete ===`);
  console.log(`Total lines processed: ${lineNumber - 1}`);
  console.log(`Records inserted/updated: ${inserted}`);
  console.log(`Errors: ${errors}`);
  console.log(`Skipped (malformed rows): ${skipped}`);
  console.log(`Skipped (portrait not found): ${skippedNoPortrait}`);
  console.log(`Unique missing portrait_ids: ${missingPortraitIds.size}`);
  if (missingPortraitIds.size > 0 && missingPortraitIds.size <= 20) {
    console.log(
      `Missing portrait_ids: ${Array.from(missingPortraitIds).join(", ")}`,
    );
  } else if (missingPortraitIds.size > 20) {
    console.log(
      `Sample missing portrait_ids (first 20): ${Array.from(missingPortraitIds).slice(0, 20).join(", ")}`,
    );
  }
  console.log(`Duplicates removed: ${duplicatesRemoved}`);
  console.log(`Final count in database: ${finalCount}`);
}

importFaceEncodings().catch(console.error);
