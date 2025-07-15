#!/usr/bin/env python
"""
Migration to create the parliament_clips table in PostgreSQL if it doesn't exist.

This migration ensures that the parliament_clips table exists in the PostgreSQL database
with all required columns, including speech_group_id.
"""

import logging
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

# Now we can import from backend
from backend.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """
    Create parliament_clips table in PostgreSQL if it doesn't exist.
    """
    logger.info("Starting migration to create parliament_clips table if it doesn't exist")
    
    # Get database URL from settings
    db_url = settings.DATABASE_URL
    logger.info(f"Using database URL: {db_url}")
    
    # Only proceed if this is a PostgreSQL database
    if 'postgresql' not in db_url.lower():
        logger.info("Not a PostgreSQL database, skipping migration")
        return True
    
    # Create engine
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        try:
            # Check if the table exists
            check_table_sql = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'parliament_clips'
                )
            """)
            
            result = conn.execute(check_table_sql)
            table_exists = result.scalar()
            
            if table_exists:
                logger.info("Table 'parliament_clips' already exists in PostgreSQL database")
                
                # Check if speech_group_id column exists
                check_column_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'parliament_clips' AND column_name = 'speech_group_id'
                """)
                result = conn.execute(check_column_sql)
                column_exists = result.fetchone() is not None
                
                if not column_exists:
                    logger.info("Adding speech_group_id column to parliament_clips table")
                    alter_table_sql = text("ALTER TABLE parliament_clips ADD COLUMN speech_group_id TEXT")
                    conn.execute(alter_table_sql)
                    conn.commit()
                    logger.info("Successfully added speech_group_id column")
                else:
                    logger.info("Column speech_group_id already exists in parliament_clips table")
                
                return True
            
            # Create the parliament_clips table with all required columns
            logger.info("Creating parliament_clips table in PostgreSQL database")
            create_table_sql = text("""
                CREATE TABLE parliament_clips (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    start_timestamp FLOAT,
                    end_timestamp FLOAT,
                    duration FLOAT,
                    member_id INTEGER,
                    speech_group_id TEXT,
                    metadata JSONB
                )
            """)
            
            conn.execute(create_table_sql)
            
            # Create indexes for better performance
            logger.info("Creating indexes on parliament_clips table")
            
            # Index on member_id for quick lookups by member
            member_index_sql = text("CREATE INDEX idx_parliament_clips_member_id ON parliament_clips (member_id)")
            conn.execute(member_index_sql)
            
            # Index on speech_group_id for quick lookups by speech group
            speech_group_index_sql = text("CREATE INDEX idx_parliament_clips_speech_group_id ON parliament_clips (speech_group_id)")
            conn.execute(speech_group_index_sql)
            
            # Index on start_timestamp for range queries
            start_time_index_sql = text("CREATE INDEX idx_parliament_clips_start_timestamp ON parliament_clips (start_timestamp)")
            conn.execute(start_time_index_sql)
            
            # GIN index on metadata for efficient JSON queries
            metadata_index_sql = text("CREATE INDEX idx_parliament_clips_metadata ON parliament_clips USING GIN (metadata)")
            conn.execute(metadata_index_sql)
            
            conn.commit()
            logger.info("Successfully created parliament_clips table with all required columns and indexes")
            
            return True
            
        except SQLAlchemyError as e:
            conn.rollback()
            logger.error(f"Error during migration: {str(e)}")
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
