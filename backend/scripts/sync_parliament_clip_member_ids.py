#!/usr/bin/env python
"""
Script to synchronize member IDs between SQLite clips database and PostgreSQL Speaker records.
This script ensures that each unique member_id in the SQLite database has a corresponding
Speaker record in PostgreSQL, allowing for proper export to Supabase.

UPDATED: This script now prioritizes numeric member IDs and uses -1 as a special ID for
unknown members (previously "default_unknown"). It converts UUIDs to numeric IDs where possible
and ensures consistent ID handling between SQLite and PostgreSQL databases.
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
        member_ids = [row[0] for row in cursor.fetchall()]
        
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
    """Check if a Speaker record exists for the given member_id"""
    try:
        # Try to convert member_id to integer if possible for consistent comparison
        try:
            numeric_id = int(member_id)
            member_id_str = str(numeric_id)
        except (ValueError, TypeError):
            member_id_str = str(member_id)
            numeric_id = None
        
        # First check by numeric member_id (preferred method)
        if numeric_id is not None:
            result = db_session.execute(
                text("SELECT id, name, parliament_id, member_id FROM speakers WHERE member_id = :member_id"),
                {"member_id": member_id_str}
            ).fetchone()
            
            if result:
                return True, result
        
        # Then try by parliament_id
        result = db_session.execute(
            text("SELECT id, name, parliament_id, member_id FROM speakers WHERE parliament_id = :member_id"),
            {"member_id": member_id_str}
        ).fetchone()
        
        if result:
            return True, result
        
        # Try to match by UUID if the member_id is a UUID
        if '-' in member_id_str and len(member_id_str) > 30:
            try:
                result = db_session.execute(
                    text("SELECT id, name, parliament_id, member_id FROM speakers WHERE id::text = :uuid_str"),
                    {"uuid_str": member_id_str}
                ).fetchone()
                if result:
                    return True, result
            except Exception:
                pass  # Ignore UUID parsing errors
            pass
            
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
        
        # Try to convert member_id to integer if possible for consistent storage
        try:
            numeric_id = int(member_id)
            member_id_str = str(numeric_id)
        except (ValueError, TypeError):
            # If conversion fails and it's a UUID, keep as is
            if isinstance(member_id, str) and '-' in member_id and len(member_id) > 30:
                member_id_str = member_id
                logger.warning(f"Using UUID as member_id: {member_id_str}")
            else:
                # For invalid or unknown member_id, use -1
                member_id_str = "-1"
                logger.warning(f"Invalid member_id format: {member_id}, using -1 instead")
        
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
                "member_id": member_id_str,  # Use numeric ID when possible
                "parliament_id": member_id_str,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        )
        
        db_session.commit()
        logger.info(f"Created new Speaker for member_id {member_id_str} with name '{name}'")
        
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

def ensure_speakers_table_exists(engine):
    """Ensure that the speakers table exists with all required columns"""
    try:
        # Check if the speakers table exists
        with engine.connect() as conn:
            result = conn.execute(text("""SELECT EXISTS (SELECT FROM information_schema.tables 
                                      WHERE table_schema = 'public' 
                                      AND table_name = 'speakers')""")).scalar()
            
            if not result:
                logger.info("Creating speakers table as it doesn't exist")
                # Create the speakers table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS speakers (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        photo_url TEXT,
                        party VARCHAR(255),
                        constituency VARCHAR(255),
                        member_id VARCHAR(255),
                        parliament_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                
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
        logger.error(traceback.format_exc())
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
    
    for member_id in member_ids:
        if not member_id:
            logger.warning(f"Skipping empty member_id")
            continue
        
        # Handle special case for default_unknown - map to -1 instead of skipping
        if member_id == "default_unknown":
            logger.info(f"Found default_unknown member_id, creating special record with ID -1")
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
            continue
            
        info = member_info.get(member_id, {})
        exists, speaker = check_speaker_exists(db_session, member_id)
        
        if exists:
            logger.info(f"Speaker already exists for member_id {member_id}: {speaker}")
            already_exists_count += 1
            continue
            
        success, new_speaker = create_speaker_for_member_id(db_session, member_id, info)
        if success:
            success_count += 1
        else:
            failure_count += 1
    
    logger.info(f"Synchronization complete. Results:")
    logger.info(f"  - Total member IDs: {len(member_ids)}")
    logger.info(f"  - Already existed: {already_exists_count}")
    logger.info(f"  - Successfully created: {success_count}")
    logger.info(f"  - Special cases handled (default_unknown → -1): {special_cases_count}")
    logger.info(f"  - Failed to create: {failure_count}")
    
    # Check if we have a record for the special -1 ID (unknown member)
    exists, _ = check_speaker_exists(db_session, -1)
    if not exists:
        logger.warning("No record exists for special ID -1 (unknown member). This may cause issues with unidentified speakers.")
        logger.warning("Consider running this script again or manually creating a record for ID -1.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
