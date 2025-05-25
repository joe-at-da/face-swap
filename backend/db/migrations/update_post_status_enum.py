#!/usr/bin/env python
"""
Migration to update the post_status_enum type to include all necessary values.
"""

import logging
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.sql import text

from backend.core.config import settings

logger = logging.getLogger(__name__)

def run_migration():
    """Update the post_status_enum type to include all necessary values."""
    logger.info("Starting migration: update_post_status_enum")
    
    try:
        # Create a connection to the database
        engine = create_engine(settings.DATABASE_URL)
        conn = engine.connect()
        
        # Check if the enum already has the values we need
        check_query = text("""
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'post_status_enum'
            ORDER BY e.enumsortorder;
        """)
        
        result = conn.execute(check_query)
        existing_values = [row[0] for row in result]
        logger.info(f"Existing enum values: {existing_values}")
        
        # Define all the values that should be in the enum
        required_values = ['PENDING', 'PUBLISHED', 'FAILED', 'SCHEDULED', 'DRAFT', 'POSTED']
        missing_values = [value for value in required_values if value not in existing_values]
        
        if not missing_values:
            logger.info("No missing enum values, skipping migration")
            return
        
        logger.info(f"Missing enum values: {missing_values}")
        
        # We need to create a new enum type with all values, then swap it with the old one
        # This is because PostgreSQL doesn't allow adding values to existing enum types directly
        
        # Step 1: Create a new enum type with all values
        create_new_enum = text("""
            CREATE TYPE post_status_enum_new AS ENUM (
                'PENDING', 'PUBLISHED', 'FAILED', 'SCHEDULED', 'DRAFT', 'POSTED'
            );
        """)
        conn.execute(create_new_enum)
        
        # Step 2: Update the column to use the new enum type
        # First, we need to create a temporary column with the new type
        add_temp_column = text("""
            ALTER TABLE social_posts ADD COLUMN status_new post_status_enum_new;
        """)
        conn.execute(add_temp_column)
        
        # Step 3: Copy data from old column to new column with appropriate casting
        # We need to handle each value separately to ensure proper conversion
        for old_value in existing_values:
            # For each existing value, map it to the corresponding new value
            new_value = old_value  # In most cases, the value stays the same
            
            # Update the temporary column
            update_temp = text(f"""
                UPDATE social_posts 
                SET status_new = '{new_value}'::post_status_enum_new 
                WHERE status = '{old_value}'::post_status_enum;
            """)
            conn.execute(update_temp)
        
        # Step 4: Drop the old column and rename the new one
        drop_old_column = text("""
            ALTER TABLE social_posts DROP COLUMN status;
            ALTER TABLE social_posts RENAME COLUMN status_new TO status;
        """)
        conn.execute(drop_old_column)
        
        # Step 5: Drop the old enum type
        drop_old_enum = text("""
            DROP TYPE post_status_enum;
        """)
        conn.execute(drop_old_enum)
        
        # Step 6: Rename the new enum type to the original name
        rename_enum = text("""
            ALTER TYPE post_status_enum_new RENAME TO post_status_enum;
        """)
        conn.execute(rename_enum)
        
        logger.info("Successfully updated post_status_enum type")
        
    except Exception as e:
        logger.error(f"Error updating post_status_enum: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
    
    logger.info("Completed migration: update_post_status_enum")
