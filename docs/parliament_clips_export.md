# Parliament Clips Export Documentation

This document explains the process of exporting Parliament Clips from the local SQLite database to Supabase PostgreSQL database.

## Overview

The Parliament Clips export process involves:
1. Loading clips from the local SQLite database
2. Converting clips to a format compatible with the Supabase schema
3. Validating required fields and data types
4. Inserting clips into the `parliament_member_clips` table in Supabase

## Key Components

### Database Schema

#### Local SQLite Database
- Clips are stored in the `parliament_clips` table
- Each clip has metadata including video_id, speaker information, etc.

#### Supabase PostgreSQL Database
- Clips are stored in the `parliament_member_clips` table
- The `parliament_members` table contains member information with:
  - `id`: UUID primary key
  - `member_id`: Integer identifier (used as foreign key in clips table)

### Export Process Flow

1. **Recognition Events Processing**
   - Recognition events are processed to identify speakers
   - Speaker events are mapped to clip records

2. **Data Sanitization**
   - Clip data is sanitized to ensure JSON serializability
   - Dates are converted to ISO strings
   - Non-serializable types are converted to strings

3. **Field Mapping**
   - Fields are mapped to match the Supabase schema
   - Required fields are validated (`member_id`, `transcript`, `full_video_path`, etc.)
   - Fields that should not be inserted are excluded (`is_deleted`, `deleted_at`, etc.)

4. **Member ID Validation**
   - `member_id` must be a valid integer
   - Non-numeric member IDs are rejected with clear error messages
   - The system validates that the integer `member_id` exists in the `parliament_members` table
   - If validation fails, the clip is not exported and an error is logged

5. **Insertion**
   - Batch insertion is attempted first
   - If batch insertion fails, per-clip insertion is attempted

## Important Notes

- The `member_id` field in `parliament_member_clips` must be an integer that matches a `member_id` in the `parliament_members` table
- The system strictly enforces numeric member IDs - no UUIDs or other formats are accepted
- No fallback mechanisms are used for invalid member IDs - errors are reported transparently
- The `status` field uses an enum with valid values like `pending_review`

## Synchronization Tools

### sync_parliament_clip_member_ids.py

This script synchronizes member IDs between the SQLite database and PostgreSQL:

```bash
# Run the synchronization script
python backend/scripts/sync_parliament_clip_member_ids.py

# Run with debug logging
python backend/scripts/sync_parliament_clip_member_ids.py --debug
```

The script performs the following operations:
- Filters out non-numeric member IDs from the SQLite database
- Ensures all numeric member IDs have corresponding Speaker records in PostgreSQL
- Creates Speaker records for valid member IDs if they don't exist
- Provides detailed logging of all operations and errors

## Verification Tools

### verify_supabase_export.py

This script verifies that Parliament Clips have been successfully exported to Supabase:

```bash
# Run all checks
python backend/scripts/verify_supabase_export.py

# Check clips for a specific video ID
python backend/scripts/verify_supabase_export.py 573

# Run specific checks
python backend/scripts/verify_supabase_export.py --check-sqlite --check-supabase
```

The script performs the following checks:
- Verifies clips in the local SQLite database
- Checks member_id mapping between SQLite and Supabase
- Validates that clips were successfully exported to Supabase
- Provides detailed reporting on any issues found

## Troubleshooting

### Common Issues

1. **Invalid input syntax for type integer**
   - Cause: `member_id` is not a valid integer
   - Solution: Ensure all member IDs in the SQLite database are valid integers

2. **Foreign key constraint violation**
   - Cause: `member_id` does not exist in the `parliament_members` table
   - Solution: Run the sync_parliament_clip_member_ids.py script to create Speaker records

3. **JSON serialization errors**
   - Cause: Non-serializable data types in clip records
   - Solution: Sanitize clip data before insertion, converting dates to strings and handling unknown types

4. **Missing required fields**
   - Cause: Required fields not present in clip data
   - Solution: Validate required fields before export

5. **Export path validation errors**
   - Cause: Invalid or missing export paths
   - Solution: Check that export paths are correctly generated and accessible
