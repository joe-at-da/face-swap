#!/usr/bin/env python
"""
Migration to add speech_group_id column to parliament_clips table.

This migration ensures that the speech_group_id column exists in the parliament_clips table
for both SQLite and PostgreSQL databases. This column is used to maintain speaker attribution
consistency across continuous speech segments.
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
    Add speech_group_id column to parliament_clips table if it doesn't exist.
    """
    logger.info("Starting migration to add speech_group_id column to parliament_clips table")
    
    # Get database URL from settings
    db_url = settings.DATABASE_URL
    logger.info(f"Using database URL: {db_url}")
    
    # Create engine
    engine = create_engine(db_url)
    
    # Determine database type
    is_sqlite = 'sqlite' in db_url.lower()
    
    with engine.connect() as conn:
        try:
            # First check if the table exists
            if is_sqlite:
                # SQLite approach
                check_table_sql = text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='parliament_clips'
                """)
            else:
                # PostgreSQL approach
                check_table_sql = text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'parliament_clips'
                    )
                """)
            
            result = conn.execute(check_table_sql)
            table_exists = result.scalar()
            
            if not table_exists:
                logger.warning("Table 'parliament_clips' does not exist, skipping migration")
                return
            
            # Check if column exists
            if is_sqlite:
                # SQLite approach
                check_column_sql = text("PRAGMA table_info(parliament_clips)")
                result = conn.execute(check_column_sql)
                columns = [row[1] for row in result]
                column_exists = 'speech_group_id' in columns
            else:
                # PostgreSQL approach
                check_column_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'parliament_clips' AND column_name = 'speech_group_id'
                """)
                result = conn.execute(check_column_sql)
                column_exists = result.fetchone() is not None
            
            # Add column if it doesn't exist
            if not column_exists:
                logger.info("Adding speech_group_id column to parliament_clips table")
                alter_table_sql = text("ALTER TABLE parliament_clips ADD COLUMN speech_group_id TEXT")
                conn.execute(alter_table_sql)
                conn.commit()
                logger.info("Successfully added speech_group_id column")
            else:
                logger.info("Column speech_group_id already exists in parliament_clips table")
            
        except SQLAlchemyError as e:
            conn.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise
    
    logger.info("Migration completed successfully")

if __name__ == "__main__":
    run_migration()
