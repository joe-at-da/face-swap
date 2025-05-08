"""
Migration script to add recognition_progress column to the capture_sessions table.
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
    """Run the migration to add recognition_progress column."""
    logger.info("Starting migration to add recognition_progress column")
    
    try:
        # Create SQLAlchemy engine
        engine = create_engine(settings.DATABASE_URL)
        
        # Check if the column already exists
        inspector = sa.inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('capture_sessions')]
        
        if 'recognition_progress' in columns:
            logger.info("Column recognition_progress already exists, skipping migration")
            return
        
        # Add the column
        logger.info("Adding recognition_progress column to capture_sessions table")
        with engine.begin() as conn:
            conn.execute(sa.text(
                "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS recognition_progress TEXT"
            ))
        
        # Add other columns if they don't exist
        missing_columns = []
        if 'recognition_status' not in columns:
            missing_columns.append("recognition_status VARCHAR(50)")
        if 'recognition_started_at' not in columns:
            missing_columns.append("recognition_started_at TIMESTAMP WITH TIME ZONE")
        if 'recognition_completed_at' not in columns:
            missing_columns.append("recognition_completed_at TIMESTAMP WITH TIME ZONE")
        if 'recognition_results' not in columns:
            missing_columns.append("recognition_results TEXT")
            
        if missing_columns:
            logger.info(f"Adding additional recognition columns: {', '.join(missing_columns)}")
            for column_def in missing_columns:
                column_name = column_def.split()[0]
                with engine.begin() as conn:
                    conn.execute(sa.text(
                        f"ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS {column_def}"
                    ))
                    logger.info(f"Added column: {column_name}")
        
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
