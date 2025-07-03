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
   - `member_id` is validated against the `parliament_members` table
   - If a `member_id` is not found, a fallback to a valid ID is used
   - UUID string `member_id`s are replaced with valid integer IDs

5. **Insertion**
   - Batch insertion is attempted first
   - If batch insertion fails, per-clip insertion is attempted

## Important Notes

- The `member_id` field in `parliament_member_clips` must be an integer that matches a `member_id` (not the UUID `id`) in the `parliament_members` table
- The `status` field uses an enum with valid values like `pending_review`
- The system uses UUIDs for clip `id` but requires integer `member_id`s

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
   - Cause: `member_id` is a UUID string instead of an integer
   - Solution: Use the integer `member_id` field from `parliament_members`, not the UUID `id`

2. **Foreign key constraint violation**
   - Cause: `member_id` does not exist in the `parliament_members` table
   - Solution: Validate `member_id` against `parliament_members` and use a fallback if needed

3. **JSON serialization errors**
   - Cause: Non-serializable data types in clip records
   - Solution: Sanitize clip data before insertion, converting dates to strings and handling unknown types

4. **Missing required fields**
   - Cause: Required fields not present in clip data
   - Solution: Validate required fields and provide defaults where possible
