import { createClient } from "@supabase/supabase-js";
import { Database } from "../supabaseTypes";
import * as fs from "fs";
import * as path from "path";
import * as dotenv from "dotenv";

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

type PortraitInsert =
  Database["public"]["Tables"]["parliament_member_portraits"]["Insert"];

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

async function importPortraits() {
  const csvPath = path.join(
    __dirname,
    "..",
    "backups",
    "parliament_member_portraits_rows (9).csv",
  );

  console.log("=== Importing Parliament Member Portraits ===");
  console.log(`Supabase URL: ${supabaseUrl}`);
  console.log(`CSV File: ${csvPath}`);

  if (!fs.existsSync(csvPath)) {
    console.error(`Error: CSV file not found at ${csvPath}`);
    process.exit(1);
  }

  // Check current count
  const { count: currentCount } = await supabase
    .from("parliament_member_portraits")
    .select("*", { count: "exact", head: true });

  console.log(`\nCurrent count in database: ${currentCount}`);

  // Get all existing member_ids to filter portraits (paginate to get all)
  console.log("Fetching existing member IDs...");
  const validMemberIds = new Set<number>();
  let page = 0;
  const pageSize = 1000;

  while (true) {
    const { data: existingMembers, error: membersError } = await supabase
      .from("parliament_members")
      .select("member_id")
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (membersError) {
      console.error("Error fetching members:", membersError.message);
      process.exit(1);
    }

    if (!existingMembers || existingMembers.length === 0) break;

    for (const m of existingMembers) {
      validMemberIds.add(m.member_id);
    }

    process.stdout.write(`\rFetched ${validMemberIds.size} member IDs...`);

    if (existingMembers.length < pageSize) break;
    page++;
  }

  console.log(`\nFound ${validMemberIds.size} existing members`);

  // Read and parse CSV
  const csvContent = fs.readFileSync(csvPath, "utf-8");
  const lines = csvContent.split("\n").filter((line) => line.trim());
  const headers = parseCSVLine(lines[0]);

  console.log(`Headers: ${headers.join(", ")}`);
  console.log(`Total rows to import: ${lines.length - 1}`);

  // Process data
  const records: PortraitInsert[] = [];
  let skippedNoMember = 0;

  for (let i = 1; i < lines.length; i++) {
    const fields = parseCSVLine(lines[i]);
    if (fields.length < 12) continue;

    const [
      id,
      member_id,
      image_url,
      crop_type,
      web_version,
      is_primary,
      last_synced_at,
      created_at,
      updated_at,
      is_deleted,
      deleted_at,
      is_valid_mp_image,
      source,
    ] = fields;

    // Skip portraits for members that don't exist
    const memberId = parseInt(member_id, 10);
    if (!validMemberIds.has(memberId)) {
      skippedNoMember++;
      continue;
    }

    records.push({
      id,
      member_id: parseInt(member_id, 10),
      image_url,
      crop_type: parseInt(crop_type, 10),
      web_version: web_version === "true",
      is_primary: is_primary === "true",
      last_synced_at: last_synced_at || null,
      created_at: created_at || null,
      updated_at: updated_at || null,
      is_deleted: is_deleted === "true",
      deleted_at: deleted_at || null,
      is_valid_mp_image: is_valid_mp_image === "true",
      source: source || "parliament_api",
    });
  }

  console.log(`\nParsed ${records.length} valid records`);
  console.log(`Skipped ${skippedNoMember} portraits (member not found)`);

  // Deduplicate by ID (keep last occurrence)
  const recordsById = new Map<string, PortraitInsert>();
  for (const record of records) {
    recordsById.set(record.id!, record);
  }
  const deduplicatedRecords = Array.from(recordsById.values());
  const duplicatesRemoved = records.length - deduplicatedRecords.length;

  if (duplicatesRemoved > 0) {
    console.log(
      `Removed ${duplicatesRemoved} duplicate IDs (keeping last occurrence)`,
    );
  }
  console.log(`Records to insert: ${deduplicatedRecords.length}`);

  // Insert in batches
  const BATCH_SIZE = 500;
  let inserted = 0;
  let errors = 0;
  const failedRecords: Array<{ record: PortraitInsert; error: string }> = [];

  for (let i = 0; i < deduplicatedRecords.length; i += BATCH_SIZE) {
    const batch = deduplicatedRecords.slice(i, i + BATCH_SIZE);
    const { error } = await supabase
      .from("parliament_member_portraits")
      .upsert(batch, { onConflict: "id" });

    if (error) {
      console.error(
        `\nError inserting batch ${Math.floor(i / BATCH_SIZE) + 1}:`,
        error.message,
      );
      console.error(`Error code: ${error.code}`);
      console.error(`Error details: ${error.details}`);
      console.error(`Error hint: ${error.hint}`);

      // Try to insert records one by one to identify the problematic ones
      console.log(
        `\nRetrying batch records individually to identify failures...`,
      );
      for (const record of batch) {
        const { error: singleError } = await supabase
          .from("parliament_member_portraits")
          .upsert(record, { onConflict: "id" });

        if (singleError) {
          errors++;
          failedRecords.push({
            record,
            error: `${singleError.code}: ${singleError.message} - ${singleError.details || ""}`,
          });
          console.error(`\n  Failed record:`);
          console.error(`    ID: ${record.id}`);
          console.error(`    Member ID: ${record.member_id}`);
          console.error(`    Image URL: ${record.image_url}`);
          console.error(`    Error: ${singleError.message}`);
        } else {
          inserted++;
        }
      }
    } else {
      inserted += batch.length;
      process.stdout.write(
        `\rInserted: ${inserted}/${deduplicatedRecords.length}`,
      );
    }
  }

  // Log all failed records summary
  if (failedRecords.length > 0) {
    console.log(`\n\n=== Failed Records Summary ===`);
    console.log(`Total failed: ${failedRecords.length}`);

    // Group failures by error type
    const errorGroups = failedRecords.reduce(
      (acc, item) => {
        const key = item.error;
        if (!acc[key]) acc[key] = [];
        acc[key].push(item.record);
        return acc;
      },
      {} as Record<string, PortraitInsert[]>,
    );

    for (const [errorMsg, records] of Object.entries(errorGroups)) {
      console.log(`\nError: ${errorMsg}`);
      console.log(`Count: ${records.length}`);
      console.log(
        `Sample member_ids: ${records
          .slice(0, 5)
          .map((r) => r.member_id)
          .join(", ")}`,
      );
    }
  }

  console.log("\n");

  // Verify final count
  const { count: finalCount } = await supabase
    .from("parliament_member_portraits")
    .select("*", { count: "exact", head: true });

  console.log(`\n=== Import Complete ===`);
  console.log(`Records inserted/updated: ${inserted}`);
  console.log(`Errors: ${errors}`);
  console.log(`Skipped (member not found): ${skippedNoMember}`);
  console.log(`Duplicates removed: ${duplicatesRemoved}`);
  console.log(`Final count in database: ${finalCount}`);
}

importPortraits().catch(console.error);
