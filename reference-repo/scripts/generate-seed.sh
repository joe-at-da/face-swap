#!/bin/bash
# =============================================================================
# Generate supabase/seed.sql from production database
# Usage: ./scripts/generate-seed.sh [PROD_DB_URL]
#
# Extracts data from 6 parliament tables, NULLs out large vector embeddings,
# and generates an idempotent seed file (INSERT ON CONFLICT DO NOTHING).
#
# Tables seeded (in FK dependency order):
#   1. parliament_events
#   2. parliament_members
#   3. parliament_member_contacts
#   4. parliament_member_portraits
#   5. parliament_member_face_encodings (face_encoding vector NULLed)
#   6. parliament_member_clips (transcript_embedding + description_embedding NULLed)
# =============================================================================
set -e

if [ -z "$1" ]; then
    echo "ERROR: Database URL required as argument"
    echo "Usage: ./scripts/generate-seed.sh 'postgresql://user:pass@host:port/db'"
    exit 1
fi
PROD_URL="$1"
OUTPUT="supabase/seed.sql"
TEMP_DIR=$(mktemp -d)

echo "Generating seed from production..."
echo "Output: $OUTPUT"
echo ""

# Verify connection
if ! PGSSLMODE=disable psql "$PROD_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to production database"
    exit 1
fi

# =============================================================================
# Helper: dump a table using pg_dump (for tables that need ALL rows, no modifications)
# =============================================================================
dump_table() {
    local table=$1
    local extra_args="${2:-}"
    echo "  Extracting $table..."
    PGSSLMODE=disable pg_dump "$PROD_URL" \
        --data-only \
        --column-inserts \
        --on-conflict-do-nothing \
        --table="public.$table" \
        --no-owner \
        --no-privileges \
        $extra_args \
        >> "$TEMP_DIR/$table.sql"
}

# =============================================================================
# Helper: run a custom query and generate INSERT ON CONFLICT DO NOTHING
# Uses COPY TO STDOUT (CSV) then transforms to INSERT statements
# =============================================================================
custom_dump() {
    local table=$1
    local columns=$2
    local query=$3
    local conflict_target=$4

    echo "  Extracting $table (custom)..."

    # Get CSV data from production
    PGSSLMODE=disable psql "$PROD_URL" -c "\\COPY ($query) TO STDOUT WITH (FORMAT csv, HEADER true, NULL 'SEED_NULL_MARKER')" \
        > "$TEMP_DIR/${table}_data.csv"

    local row_count=$(( $(wc -l < "$TEMP_DIR/${table}_data.csv") - 1 ))
    echo "    → $row_count rows"

    # Generate INSERT statements from CSV using Python
    python3 << PYEOF > "$TEMP_DIR/$table.sql"
import csv
import sys

table = "$table"
columns = "$columns"
conflict = "$conflict_target"

col_list = [c.strip() for c in columns.split(',')]

with open("$TEMP_DIR/${table}_data.csv", 'r') as f:
    reader = csv.reader(f)
    header = next(reader)  # skip header

    batch = []
    batch_size = 100

    for row in reader:
        values = []
        for val in row:
            if val == 'SEED_NULL_MARKER':
                values.append('NULL')
            else:
                # Quote all values as string literals — PG coerces to target type
                escaped = val.replace("'", "''")
                values.append(f"'{escaped}'")

        batch.append(f"({', '.join(values)})")

        if len(batch) >= batch_size:
            print(f"INSERT INTO public.{table} ({columns})")
            print("VALUES")
            print(',\n'.join(batch))
            print(f"ON CONFLICT {conflict} DO NOTHING;")
            print()
            batch = []

    # Flush remaining
    if batch:
        print(f"INSERT INTO public.{table} ({columns})")
        print("VALUES")
        print(',\n'.join(batch))
        print(f"ON CONFLICT {conflict} DO NOTHING;")
        print()

PYEOF
}

# =============================================================================
# 1. parliament_events — all non-deleted
# =============================================================================
echo "Step 1/6: parliament_events"
dump_table "parliament_events"

# =============================================================================
# 2. parliament_members — all non-deleted
# =============================================================================
echo "Step 2/6: parliament_members"
dump_table "parliament_members"

# =============================================================================
# 3. parliament_member_contacts — all rows
# =============================================================================
echo "Step 3/6: parliament_member_contacts"
dump_table "parliament_member_contacts"

# =============================================================================
# 4. parliament_member_portraits — all rows
# =============================================================================
echo "Step 4/6: parliament_member_portraits"
dump_table "parliament_member_portraits"

# =============================================================================
# 5. parliament_member_face_encodings — custom (NULL out face_encoding vector)
# =============================================================================
echo "Step 5/6: parliament_member_face_encodings"
# face_encoding is NOT NULL vector(512) — we include metadata only
# face_encoding_json is omitted (huge JSONB), face_encoding gets a zero vector via DEFAULT override
# We'll add the face_encoding column with a zero vector literal after generating INSERTs

FACE_ENC_COLUMNS="id, member_id, portrait_id, detection_confidence, encoding_quality, face_bbox_top, face_bbox_right, face_bbox_bottom, face_bbox_left, image_width, image_height, processing_model, processing_date, processing_version, is_primary_encoding, is_validated, is_active, is_deleted, deleted_at, created_at, updated_at, last_synced_at, processing_notes, error_message"

custom_dump "parliament_member_face_encodings" \
    "$FACE_ENC_COLUMNS" \
    "SELECT id, member_id, portrait_id, detection_confidence, encoding_quality, face_bbox_top, face_bbox_right, face_bbox_bottom, face_bbox_left, image_width, image_height, processing_model, processing_date, processing_version, is_primary_encoding, is_validated, is_active, is_deleted, deleted_at, created_at, updated_at, last_synced_at, processing_notes, error_message FROM parliament_member_face_encodings WHERE is_deleted = FALSE" \
    "(id)"

# Wrap face_encodings inserts: temporarily ALTER to allow NULL, insert, then set zero vector
# This avoids embedding 17k zero vectors in the SQL file
FACE_ENC_WRAPPER_FILE="$TEMP_DIR/parliament_member_face_encodings_wrapped.sql"
{
    echo "-- Temporarily allow NULL for face_encoding during seed"
    echo "ALTER TABLE public.parliament_member_face_encodings ALTER COLUMN face_encoding DROP NOT NULL;"
    echo ""
    cat "$TEMP_DIR/parliament_member_face_encodings.sql"
    echo ""
    echo "-- Restore NOT NULL constraint (zero vector placeholder for seeded rows without real encoding)"
    echo "UPDATE public.parliament_member_face_encodings SET face_encoding = (SELECT array_fill(0, ARRAY[512])::vector(512)) WHERE face_encoding IS NULL;"
    echo "ALTER TABLE public.parliament_member_face_encodings ALTER COLUMN face_encoding SET NOT NULL;"
} > "$FACE_ENC_WRAPPER_FILE"
mv "$FACE_ENC_WRAPPER_FILE" "$TEMP_DIR/parliament_member_face_encodings.sql"

# =============================================================================
# 6. parliament_member_clips — custom (NULL out embeddings, NULL processing_segment_id)
#    ALL rows for member_id=5296, plus 5 most recent per other member
# =============================================================================
echo "Step 6/6: parliament_member_clips"

CLIPS_COLUMNS="id, member_id, transcript, clip_url, full_video_path, session_date, session_type, status, processing_notes, is_deleted, deleted_at, last_synced_at, created_at, updated_at, start_timestamp, end_timestamp, duration_seconds, vertical_clip_url, thumbnail_url, vertical_thumbnail_url, session_uid, description, is_false_positive, is_unidentified, notification_sent_at"

CLIPS_QUERY="
SELECT id, member_id, transcript, clip_url, full_video_path, session_date, session_type, status::text, processing_notes, is_deleted, deleted_at, last_synced_at, created_at, updated_at, start_timestamp, end_timestamp, duration_seconds, vertical_clip_url, thumbnail_url, vertical_thumbnail_url, session_uid, description, is_false_positive, is_unidentified, notification_sent_at
FROM parliament_member_clips
WHERE member_id = 5296 AND is_deleted = FALSE

UNION ALL

SELECT id, member_id, transcript, clip_url, full_video_path, session_date, session_type, status::text, processing_notes, is_deleted, deleted_at, last_synced_at, created_at, updated_at, start_timestamp, end_timestamp, duration_seconds, vertical_clip_url, thumbnail_url, vertical_thumbnail_url, session_uid, description, is_false_positive, is_unidentified, notification_sent_at
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY created_at DESC) AS rn
    FROM parliament_member_clips
    WHERE member_id != 5296 AND is_deleted = FALSE
) ranked
WHERE rn <= 5
"

custom_dump "parliament_member_clips" \
    "$CLIPS_COLUMNS" \
    "$CLIPS_QUERY" \
    "(id)"

# =============================================================================
# Assemble final seed.sql
# =============================================================================
echo ""
echo "Assembling $OUTPUT..."

cat > "$OUTPUT" << 'HEADER'
-- =============================================================================
-- Supabase Seed File — Parliament Data
-- Generated by: scripts/generate-seed.sh
--
-- Tables: parliament_events, parliament_members, parliament_member_contacts,
--         parliament_member_portraits, parliament_member_face_encodings,
--         parliament_member_clips
--
-- Notes:
-- - Embedding vectors (transcript_embedding, description_embedding, face_encoding)
--   are omitted to keep file size manageable. Re-run embedding pipeline if needed.
-- - processing_segment_id is omitted (event_processing_segments not seeded)
-- - Uses INSERT ON CONFLICT DO NOTHING for idempotent re-runs
-- =============================================================================

-- Temporarily disable triggers during bulk load for performance
SET session_replication_role = replica;

HEADER

# Append each table's SQL in FK dependency order
for table in parliament_events parliament_members parliament_member_contacts parliament_member_portraits parliament_member_face_encodings parliament_member_clips; do
    echo "" >> "$OUTPUT"
    echo "-- =============================" >> "$OUTPUT"
    echo "-- $table" >> "$OUTPUT"
    echo "-- =============================" >> "$OUTPUT"
    cat "$TEMP_DIR/$table.sql" >> "$OUTPUT"
done

# Re-enable triggers
cat >> "$OUTPUT" << 'FOOTER'

-- Re-enable triggers
SET session_replication_role = DEFAULT;
FOOTER

# Post-process: remove pg_dump 17 directives incompatible with PG 15
# - transaction_timeout: only available in PG 17+
# - \restrict/\unrestrict: psql 17+ meta-commands
sed -i'' -e '/^SET transaction_timeout/d; /^\\restrict /d; /^\\unrestrict/d' "$OUTPUT"
# Also remove the search_path reset that pg_dump adds (it hides public schema)
sed -i'' -e "/^SELECT pg_catalog.set_config('search_path'/d" "$OUTPUT"

# Cleanup
rm -rf "$TEMP_DIR"

# Stats
FILE_SIZE=$(ls -lh "$OUTPUT" | awk '{print $5}')
LINE_COUNT=$(wc -l < "$OUTPUT")
echo ""
echo "==========================================="
echo "Seed file generated: $OUTPUT"
echo "Size: $FILE_SIZE"
echo "Lines: $LINE_COUNT"
echo "==========================================="

# Verify it's under 100MB
SIZE_BYTES=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT")
if [ "$SIZE_BYTES" -gt 104857600 ]; then
    echo "WARNING: Seed file exceeds 100MB limit!"
    exit 1
fi

echo "Success!"
