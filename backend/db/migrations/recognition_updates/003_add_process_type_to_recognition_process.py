#!/usr/bin/env python
"""
Migration to add process_type column to RecognitionProcess model.
"""

import logging
import os
import sys
from sqlalchemy import Column, String, text
from sqlalchemy.sql import func

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Add process_type column to recognition_processes table."""
    from backend.core.config import settings
    from sqlalchemy import create_engine
    
    # Create engine from settings
    engine = create_engine(settings.DATABASE_URL)
    
    logger.info("Adding process_type column to recognition_processes table")
    
    try:
        # Check if the column already exists
        with engine.connect() as connection:
            result = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'recognition_processes' AND column_name = 'process_type'"
            ))
            if result.fetchone():
                logger.info("Column process_type already exists in recognition_processes table")
                return True
            
            # Add the column
            connection.execute(text(
                "ALTER TABLE recognition_processes "
                "ADD COLUMN process_type VARCHAR(50) DEFAULT 'facial'"
            ))
            
            # Create index on the new column
            connection.execute(text(
                "CREATE INDEX ix_recognition_processes_process_type "
                "ON recognition_processes (process_type)"
            ))
            
            # Update existing records to have a default value
            connection.execute(text(
                "UPDATE recognition_processes SET process_type = 'facial' "
                "WHERE process_type IS NULL"
            ))
            
            logger.info("Successfully added process_type column to recognition_processes table")
            return True
    except Exception as e:
        logger.error(f"Error adding process_type column: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    import sys
    sys.exit(0 if success else 1)
