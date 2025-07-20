# Database Troubleshooting Guide

## Common Issues and Solutions

### Speech Group ID Assignment Issues

**Issue**: Incorrect or missing speech group IDs in parliament clips, causing fragmented speech segments or incorrect speaker attribution.

**Symptoms**:
- Multiple speech group IDs for the same continuous speech
- Temporary speech group IDs (format: `temp_XXX`) remaining in the database
- Inconsistent speaker attribution across speech segments
- Missing diarization files

**Solution**:
1. Verify diarization files are being found correctly:
   ```bash
   # Check for diarization files in common locations
   find /app/data/temp -name "*.diarization.json" -o -name "*_speakers.json"
   ```

2. Force update speech group IDs for a specific video:
   ```bash
   # Run the update_speech_groups.py script with --force flag
   python scripts/update_speech_groups.py --video_path /app/data/media/VIDEO_ID.mp4 --force
   ```

3. Check for temporary speech group IDs in the database:
   ```sql
   -- In SQLite
   SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id LIKE 'temp_%';
   ```

4. Verify speech group assignments in the database:
   ```sql
   -- In SQLite
   SELECT speech_group_id, COUNT(*) as clip_count 
   FROM parliament_clips 
   GROUP BY speech_group_id 
   ORDER BY clip_count DESC;
   ```

5. For performance optimization, consider batch processing speech group updates:
   ```python
   # Example batch update code
   with db.transaction():
       db.executemany("UPDATE parliament_clips SET speech_group_id = ? WHERE id = ?", updates)
   ```

### Missing Tables

**Issue**: 401 Unauthorized errors or 500 Internal Server errors due to missing database tables.

**Symptoms**:
- Endpoints return 401 Unauthorized even with valid authentication tokens
- Backend logs show errors like `relation "table_name" does not exist`
- Authentication works for some endpoints but not others

**Solution**:
1. Check if the required database tables exist:
   ```sql
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
   ```

2. If tables are missing, create them manually or run migrations:
   ```bash
   # Run migrations
   docker-compose -f docker-compose.dev.yml exec app alembic upgrade head
   
   # Or create tables manually
   docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d parliament_clips -c "CREATE TABLE..."
   ```

3. Ensure the model definitions match the database schema:
   - Check the model fields in the code
   - Compare with the database table structure
   - Add missing columns if needed

### Migration Issues

**Issue**: Alembic migrations fail due to dependency or type issues.

**Symptoms**:
- Errors like `type "enum_name" does not exist`
- Multiple head revisions
- Inconsistent migration history

**Solution**:
1. Check the current migration state:
   ```bash
   docker-compose -f docker-compose.dev.yml exec app alembic current
   docker-compose -f docker-compose.dev.yml exec app alembic heads
   ```

2. For multiple heads, create a merge migration:
   ```bash
   docker-compose -f docker-compose.dev.yml exec app alembic merge heads -m "merge_heads"
   ```

3. For type errors, ensure enum types are created before they're used:
   ```python
   # In your migration script
   op.execute("CREATE TYPE enum_name AS ENUM ('VALUE1', 'VALUE2', ...)")
   ```

### Authentication Issues

**Issue**: Inconsistent authentication behavior across endpoints.

**Solution**:
1. Ensure all endpoints use the same authentication dependency:
   ```python
   @router.get("/endpoint")
   async def endpoint(current_user: models.User = Depends(get_current_active_user)):
       # Function body
   ```

2. Check that the token validation is consistent:
   - The subject in the token should match how users are looked up (by ID or email)
   - The same secret key should be used for all token validation

## Specific Issues Fixed

### Capture Sessions Table Missing (2025-04-26)

**Issue**: The `/api/v1/capture` endpoint was returning 401 Unauthorized errors despite valid authentication tokens. The backend logs showed that the `capture_sessions` table did not exist.

**Root Cause**: The migration for creating the `capture_sessions` table existed but had not been applied to the database.

**Solution**:
1. Created the `capture_sessions` table manually:
   ```sql
   CREATE TABLE capture_sessions (
       id SERIAL PRIMARY KEY,
       user_id INTEGER,
       status VARCHAR(50),
       error_message VARCHAR(255),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE,
       CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id)
   );
   ```

2. Added additional columns to match the model:
   ```sql
   ALTER TABLE capture_sessions 
   ADD COLUMN title VARCHAR(255),
   ADD COLUMN description TEXT,
   ADD COLUMN source_url VARCHAR(255),
   ADD COLUMN file_path VARCHAR(255),
   ADD COLUMN file_size BIGINT,
   ADD COLUMN duration INTEGER,
   ADD COLUMN scheduled_start TIMESTAMP WITH TIME ZONE,
   ADD COLUMN scheduled_end TIMESTAMP WITH TIME ZONE,
   ADD COLUMN start_time TIMESTAMP WITH TIME ZONE,
   ADD COLUMN end_time TIMESTAMP WITH TIME ZONE;
   ```

3. Created indexes for performance:
   ```sql
   CREATE INDEX ix_capture_sessions_id ON capture_sessions (id);
   CREATE INDEX ix_capture_sessions_status ON capture_sessions (status);
   ```

**Prevention**:
1. Always run migrations after pulling new code
2. Add database schema validation on application startup
3. Implement better error handling to provide clearer error messages
