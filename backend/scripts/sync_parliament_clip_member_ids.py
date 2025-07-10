#!/usr/bin/env python
"""
Script to synchronize member IDs between SQLite clips database and PostgreSQL Speaker records.
This script ensures that each unique member_id in the SQLite database has a corresponding
Speaker record in PostgreSQL, allowing for proper export to Supabase.

UPDATED: This script now requires numeric member IDs and uses -1 as a special ID for
unknown members. It ensures consistent ID handling between SQLite and PostgreSQL databases.
UUIDs are not supported - all member IDs must be numeric integers.
"""

import os
import sys
import json
import sqlite3
import logging
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("sync_member_ids")

# Path to SQLite database
SQLITE_DB_PATH = "/app/backend/parliament_clips.db"

def setup_postgres_connection():
    """Set up connection to PostgreSQL database"""
    try:
        # Get database URL from environment or use default
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres")
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        return Session(), engine
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        return None, None

def get_unique_member_ids_from_sqlite():
    """Get all unique member_ids from the SQLite database"""
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"SQLite database not found at {SQLITE_DB_PATH}")
        return []
    
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Get all unique member_ids
        cursor.execute("SELECT DISTINCT member_id FROM parliament_clips")
        all_member_ids = [row[0] for row in cursor.fetchall()]
        
        # Filter for numeric member IDs only
        member_ids = []
        for mid in all_member_ids:
            try:
                if mid is not None:
                    # Try to convert to integer
                    int(mid)
                    member_ids.append(mid)
            except (ValueError, TypeError):
                logger.warning(f"Skipping non-numeric member_id: {mid}")
        
        logger.info(f"Filtered {len(all_member_ids)} total member IDs to {len(member_ids)} numeric member IDs")
        if len(all_member_ids) > len(member_ids):
            logger.warning(f"Skipped {len(all_member_ids) - len(member_ids)} non-numeric member IDs")
            logger.warning("Member IDs must be numeric integers, not UUIDs or other formats")
        
        # Get additional information for each member_id
        member_info = {}
        for member_id in member_ids:
            cursor.execute("""
                SELECT 
                    member_id, 
                    transcript, 
                    metadata
                FROM parliament_clips 
                WHERE member_id = ? 
                LIMIT 1
            """, (member_id,))
            
            row = cursor.fetchone()
            if row:
                metadata = {}
                try:
                    if row[2]:
                        metadata = json.loads(row[2])
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse metadata JSON for member_id {member_id}")
                
                member_info[member_id] = {
                    'member_id': row[0],
                    'transcript': row[1],
                    'member_name': metadata.get('member_name'),
                    'face_image_url': metadata.get('face_image_url')
                }
        
        conn.close()
        logger.info(f"Found {len(member_ids)} unique member IDs in SQLite database")
        return member_ids, member_info
    except Exception as e:
        logger.error(f"Error getting member IDs from SQLite: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], {}

def check_speaker_exists(db_session, member_id):
    """Check if a speaker with the given member_id already exists"""
    try:
        # Convert member_id to integer for consistent querying
        try:
            # If it's already an integer, use it directly
            if isinstance(member_id, int):
                numeric_id = member_id
            else:
                # Try to convert to integer
                numeric_id = int(member_id)
            
            # Log the conversion
            if not isinstance(member_id, int):
                logger.info(f"Converted member_id from {type(member_id).__name__} '{member_id}' to int {numeric_id}")
        except (ValueError, TypeError):
            # For invalid member_id, log error and return False
            logger.error(f"Invalid member_id format: {member_id}. Member IDs must be numeric integers.")
            return False, None
        
        # Check by numeric member_id
        try:
            result = db_session.execute(
                text("SELECT id, name, parliament_id, member_id FROM speakers WHERE member_id = :member_id"),
                {"member_id": numeric_id}
            ).fetchone()
            
            if result:
                logger.info(f"Found speaker with member_id {numeric_id}: {result}")
                return True, result
                
            # Then try by parliament_id as fallback
            result = db_session.execute(
                text("SELECT id, name, parliament_id, member_id FROM speakers WHERE parliament_id = :member_id"),
                {"member_id": str(numeric_id)}
            ).fetchone()
            
            if result:
                logger.info(f"Found speaker with parliament_id {numeric_id}: {result}")
                return True, result
                
            logger.info(f"No speaker found for member_id {numeric_id}")
            return False, None
        except Exception as query_error:
            # If there's an error in the query, log it and rollback
            logger.error(f"Error querying speakers table: {query_error}")
            db_session.rollback()
            return False, None
    except Exception as e:
        logger.error(f"Error checking if speaker exists: {e}")
        return False, None

def create_speaker_for_member_id(db_session, member_id, member_info=None):
    """Create a Speaker record for the given member_id if it doesn't exist"""
    try:
        # Check if speaker already exists
        exists, speaker = check_speaker_exists(db_session, member_id)
        if exists:
            logger.info(f"Speaker already exists for member_id {member_id}: {speaker}")
            return True, speaker
        
        # Always convert member_id to integer for consistent storage
        try:
            # If it's already an integer, use it directly
            if isinstance(member_id, int):
                numeric_id = member_id
            else:
                # Try to convert to integer
                numeric_id = int(member_id)
            
            # Log the conversion
            if not isinstance(member_id, int):
                logger.info(f"Converted member_id from {type(member_id).__name__} '{member_id}' to int {numeric_id}")
        except (ValueError, TypeError):
            # For invalid member_id, log error and return False
            logger.error(f"Invalid member_id format: {member_id}. Member IDs must be numeric integers.")
            return False, None
        
        # Generate a name for the speaker
        name = "Unknown Speaker"
        if member_info and member_info.get('member_name'):
            name = member_info['member_name']
        elif member_info and member_info.get('transcript'):
            # Use first few words of transcript as name if available
            transcript_words = member_info['transcript'].split()
            if len(transcript_words) > 2:
                name = f"{' '.join(transcript_words[:3])}..."
            elif len(transcript_words) > 0:
                name = member_info['transcript']
        
        # Get photo URL if available
        photo_url = ""
        if member_info and member_info.get('face_image_url'):
            photo_url = member_info['face_image_url']
        
        # Create new speaker
        new_id = db_session.execute(text("SELECT nextval('speakers_id_seq')")).scalar()
        
        # Insert the new speaker
        db_session.execute(
            text("""
                INSERT INTO speakers 
                (id, name, photo_url, party, constituency, member_id, parliament_id, created_at, updated_at) 
                VALUES 
                (:id, :name, :photo_url, :party, :constituency, :member_id, :parliament_id, :created_at, :updated_at)
            """),
            {
                "id": new_id,
                "name": name,
                "photo_url": photo_url,
                "party": "Unknown",  # Default party
                "constituency": "Unknown",  # Default constituency
                "member_id": numeric_id,  # Use integer for member_id
                "parliament_id": str(numeric_id),  # Keep parliament_id as string for backward compatibility
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        )
        
        db_session.commit()
        logger.info(f"Created new Speaker for member_id {member_id} with name '{name}'")
        
        # Return the newly created speaker
        new_speaker = db_session.execute(
            text("SELECT id, name, parliament_id, member_id FROM speakers WHERE id = :id"),
            {"id": new_id}
        ).fetchone()
        
        return True, new_speaker
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating speaker for member_id {member_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None

def ensure_member_id_is_integer(engine):
    """Ensure that the member_id column in the speakers table is INTEGER type"""
    try:
        with engine.connect() as conn:
            # Check the current data type of member_id column
            data_type = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'speakers' AND column_name = 'member_id'
            """)).scalar()
            
            logger.info(f"Current member_id column type: {data_type}")
            
            # If the column is not integer type, alter it
            if data_type and 'integer' not in data_type.lower():
                logger.info(f"Converting member_id column from {data_type} to INTEGER")
                
                # First, create a temporary backup of the data
                conn.execute(text("""
                    CREATE TEMP TABLE speakers_backup AS 
                    SELECT * FROM speakers
                """))
                
                # Try to alter the column type directly
                try:
                    # First convert any non-numeric values to -1
                    conn.execute(text("""
                        UPDATE speakers 
                        SET member_id = '-1' 
                        WHERE member_id ~ '[^0-9]' OR member_id IS NULL
                    """))
                    
                    # Then alter the column type
                    conn.execute(text("""
                        ALTER TABLE speakers 
                        ALTER COLUMN member_id TYPE INTEGER USING (member_id::integer)
                    """))
                    
                    conn.commit()
                    logger.info("Successfully converted member_id column to INTEGER")
                    return True
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error converting column directly: {e}")
                    
                    # If direct conversion fails, try recreating the table
                    try:
                        # Rename the old table
                        conn.execute(text("ALTER TABLE speakers RENAME TO speakers_old"))
                        
                        # Create new table with correct schema
                        conn.execute(text("""
                            CREATE TABLE speakers (
                                id SERIAL PRIMARY KEY,
                                name VARCHAR(255) NOT NULL,
                                photo_url TEXT,
                                party VARCHAR(255),
                                constituency VARCHAR(255),
                                member_id INTEGER,
                                parliament_id VARCHAR(255),
                                created_at TIMESTAMP DEFAULT NOW(),
                                updated_at TIMESTAMP DEFAULT NOW()
                            )
                        """))
                        
                        # Copy data with conversion
                        conn.execute(text("""
                            INSERT INTO speakers (id, name, photo_url, party, constituency, member_id, parliament_id, created_at, updated_at)
                            SELECT id, name, photo_url, party, constituency, 
                                CASE 
                                    WHEN member_id ~ '^[0-9]+$' THEN member_id::integer 
                                    ELSE -1 
                                END, 
                                parliament_id, created_at, updated_at
                            FROM speakers_old
                        """))
                        
                        # Drop the old table
                        conn.execute(text("DROP TABLE speakers_old"))
                        
                        conn.commit()
                        logger.info("Successfully recreated speakers table with INTEGER member_id")
                        return True
                    except Exception as recreate_error:
                        conn.rollback()
                        logger.error(f"Error recreating table: {recreate_error}")
                        return False
            else:
                logger.info("member_id column is already INTEGER type")
                return True
    except Exception as e:
        logger.error(f"Error checking or altering member_id column: {e}")
        return False

def ensure_speakers_table_exists(engine):
    """Ensure that the speakers table exists with all required columns"""
    try:
        # Check if the speakers table exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'speakers')
            """)).scalar()
            
            if not result:
                logger.info("Creating speakers table as it doesn't exist")
                # Create the speakers table with INTEGER member_id
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS speakers (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        photo_url TEXT,
                        party VARCHAR(255),
                        constituency VARCHAR(255),
                        member_id INTEGER,
                        parliament_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                
                conn.commit()
                logger.info("Successfully created speakers table with INTEGER member_id")
                
                # Create the speakers_id_seq sequence if it doesn't exist
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'speakers_id_seq') THEN
                            CREATE SEQUENCE speakers_id_seq START 1;
                        END IF;
                    END
                    $$;
                """))
                
                conn.commit()
                logger.info("Successfully created speakers table")
            else:
                # Check if all required columns exist
                columns = ['id', 'name', 'photo_url', 'party', 'constituency', 'member_id', 'parliament_id', 'created_at', 'updated_at']
                missing_columns = []
                
                for column in columns:
                    column_exists = conn.execute(text(f"""
                        SELECT EXISTS (SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'speakers' 
                        AND column_name = '{column}')
                    """)).scalar()
                    
                    if not column_exists:
                        missing_columns.append(column)
                
                if missing_columns:
                    logger.info(f"Adding missing columns to speakers table: {missing_columns}")
                    
                    for column in missing_columns:
                        if column == 'id':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN id SERIAL PRIMARY KEY"))
                        elif column == 'name':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT 'Unknown'"))
                        elif column == 'photo_url':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN photo_url TEXT"))
                        elif column == 'party':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN party VARCHAR(255)"))
                        elif column == 'constituency':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN constituency VARCHAR(255)"))
                        elif column == 'member_id':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN member_id VARCHAR(255)"))
                        elif column == 'parliament_id':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN parliament_id VARCHAR(255)"))
                        elif column == 'created_at':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN created_at TIMESTAMP DEFAULT NOW()"))
                        elif column == 'updated_at':
                            conn.execute(text("ALTER TABLE speakers ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()"))
                    
                    conn.commit()
                    logger.info("Successfully added missing columns to speakers table")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring speakers table exists: {e}")
        import traceback
        return False

def main():
    """Main function to synchronize member IDs"""
    logger.info("Starting member ID synchronization")
    
    # Connect to PostgreSQL
    db_session, engine = setup_postgres_connection()
    if not db_session or not engine:
        logger.error("Failed to connect to PostgreSQL database")
        return False
        
    # Ensure the speakers table exists
    if not ensure_speakers_table_exists(engine):
        logger.error("Failed to ensure speakers table exists")
        return False
    
    # Ensure member_id column is INTEGER
    if not ensure_member_id_is_integer(engine):
        logger.error("Failed to ensure member_id column is INTEGER")
        return False
        
    # Commit any pending transactions to start with a clean slate
    db_session.commit()
    
    # Get unique member IDs from SQLite
    member_ids, member_info = get_unique_member_ids_from_sqlite()
    if not member_ids:
        logger.warning("No member IDs found in SQLite database")
        return True
    
    # Create Speaker records for each member_id
    success_count = 0
    failure_count = 0
    already_exists_count = 0
    special_cases_count = 0
    failed_member_ids = []
    
    for member_id in member_ids:
        if not member_id:
            logger.warning(f"Skipping empty member_id")
            continue
        
        # Handle special case for non-numeric member IDs
        try:
            # Try to convert to integer
            numeric_id = int(member_id) if not isinstance(member_id, int) else member_id
        except (ValueError, TypeError):
            logger.error(f"Skipping non-numeric member_id: {member_id}. Member IDs must be numeric integers.")
            failure_count += 1
            failed_member_ids.append(str(member_id))
            continue
            
        # Special handling for unknown members (ID -1)
        if numeric_id == -1:
            logger.info(f"Found special ID -1 for unknown members")
            # Check if -1 already exists
            exists, speaker = check_speaker_exists(db_session, -1)
            if exists:
                logger.info(f"Special ID -1 already exists: {speaker}")
                already_exists_count += 1
                special_cases_count += 1
                continue
                
            # Create special record for unknown member
            success, new_speaker = create_speaker_for_member_id(db_session, -1, {"member_name": "Unknown MP"})
            if success:
                logger.info(f"Created special record for unknown members with ID -1")
                success_count += 1
                special_cases_count += 1
            else:
                failure_count += 1
                failed_member_ids.append("-1")
            continue
            
        info = member_info.get(member_id, {})
        exists, speaker = check_speaker_exists(db_session, member_id)
        
        if exists:
            logger.info(f"Speaker already exists for member_id {member_id}: {speaker}")
            already_exists_count += 1
            continue
        
        # No special handling for specific member IDs - all should go through the same process
        # This ensures consistent handling of all numeric member IDs
            
        success, new_speaker = create_speaker_for_member_id(db_session, member_id, info)
        if success:
            success_count += 1
        else:
            failure_count += 1
            failed_member_ids.append(str(member_id))
    
    logger.info(f"Synchronization complete. Results:")
    logger.info(f"  - Total member IDs: {len(member_ids)}")
    logger.info(f"  - Already existed: {already_exists_count}")
    logger.info(f"  - Successfully created: {success_count}")
    logger.info(f"  - Special cases handled (default_unknown → -1): {special_cases_count}")
    logger.info(f"  - Failed to create: {failure_count}")
    
    # Log specific member IDs that failed to synchronize
    if failed_member_ids:
        logger.warning(f"After synchronization, {len(failed_member_ids)} member IDs are still missing in PostgreSQL")
        for member_id in failed_member_ids:
            logger.warning(f"Still missing member ID: {member_id}")
    else:
        logger.info("All member IDs were successfully synchronized")
    
    # Check if we have a record for the special -1 ID (unknown member)
    exists, _ = check_speaker_exists(db_session, -1)
    if not exists:
        logger.warning("No record exists for special ID -1 (unknown member). This may cause issues with unidentified speakers.")
        logger.warning("Consider running this script again or manually creating a record for ID -1.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
