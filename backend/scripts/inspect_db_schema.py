#!/usr/bin/env python3
"""
Inspect the SQLite database schema
"""

import os
import sys
import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def inspect_db_schema():
    """Inspect the SQLite database schema."""
    logger.info("=== Inspecting SQLite Database Schema ===")
    
    # Get the database path
    db_path = "/app/backend/parliament_clips.db"
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        return False
    
    logger.info(f"Database file found at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    logger.info(f"Found {len(tables)} tables in the database:")
    for table in tables:
        table_name = table[0]
        logger.info(f"  - {table_name}")
        
        # Get schema for this table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        logger.info(f"    Columns in {table_name}:")
        for column in columns:
            col_id, col_name, col_type, not_null, default_val, is_pk = column
            logger.info(f"      - {col_name} ({col_type}){' PRIMARY KEY' if is_pk else ''}")
    
    # Close the connection
    conn.close()
    
    return True

if __name__ == "__main__":
    inspect_db_schema()
