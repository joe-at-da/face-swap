"""
Migration script to add transcription-related columns to the capture_sessions table.
"""

import logging
import os
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add transcription-related columns."""
    logger.info("Starting migration to add transcription-related columns")
    
    try:
        # Create SQLAlchemy engine
        engine = create_engine(settings.DATABASE_URL)
        
        # Check if the columns already exist
        inspector = sa.inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('capture_sessions')]
        
        # Define the columns to add
        columns_to_add = [
            ("transcription_status", "VARCHAR(50)"),
            ("transcription_path", "TEXT"),
            ("transcription_error", "TEXT"),
            ("transcription_completed_at", "TIMESTAMP WITH TIME ZONE"),
            ("transcription_results", "TEXT")
        ]
        
        # Add each column if it doesn't exist
        for column_name, column_type in columns_to_add:
            if column_name not in columns:
                logger.info(f"Adding {column_name} column to capture_sessions table")
                with engine.begin() as conn:
                    conn.execute(sa.text(
                        f"ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
                    ))
                logger.info(f"Added column: {column_name}")
            else:
                logger.info(f"Column {column_name} already exists, skipping")
        
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
    finally:
        logger.info("Migration process finished")
        # Explicitly dispose of the engine to close connections
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    run_migration()
