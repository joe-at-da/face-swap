#!/usr/bin/env python
"""
Migration to enhance recognition data storage in the database.
This migration adds additional columns for storing timeline data and improves the structure
of recognition results.
"""

import logging
import json
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from backend.core.config import settings

logger = logging.getLogger(__name__)

def run_migration():
    """Enhance recognition data storage in the database."""
    logger.info("Starting migration: enhance_recognition_storage")
    
    try:
        # Create a connection to the database
        engine = create_engine(settings.DATABASE_URL)
        conn = engine.connect()
        
        # Check if the recognition_events table already exists
        check_table_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'recognition_events'
            );
        """)
        
        result = conn.execute(check_table_query)
        table_exists = result.scalar()
        
        if not table_exists:
            # Create the recognition_events table
            create_table_query = text("""
                CREATE TABLE recognition_events (
                    id SERIAL PRIMARY KEY,
                    capture_session_id INTEGER REFERENCES capture_sessions(id) ON DELETE CASCADE,
                    event_type VARCHAR(50) NOT NULL,
                    start_time FLOAT NOT NULL,
                    end_time FLOAT NOT NULL,
                    confidence FLOAT,
                    person_id INTEGER,
                    person_name VARCHAR(255),
                    data JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                CREATE INDEX idx_recognition_events_capture_session_id ON recognition_events(capture_session_id);
                CREATE INDEX idx_recognition_events_event_type ON recognition_events(event_type);
                CREATE INDEX idx_recognition_events_start_time ON recognition_events(start_time);
                CREATE INDEX idx_recognition_events_person_id ON recognition_events(person_id);
            """)
            
            conn.execute(create_table_query)
            logger.info("Created recognition_events table")
        
        # Check if the face_detection_results column exists in capture_sessions
        check_column_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'capture_sessions' 
                AND column_name = 'face_detection_results'
            );
        """)
        
        result = conn.execute(check_column_query)
        column_exists = result.scalar()
        
        if not column_exists:
            # Add the face_detection_results column to capture_sessions
            add_column_query = text("""
                ALTER TABLE capture_sessions 
                ADD COLUMN face_detection_results TEXT;
            """)
            
            conn.execute(add_column_query)
            logger.info("Added face_detection_results column to capture_sessions")
        
        # Check if the timeline_data column exists in capture_sessions
        check_column_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'capture_sessions' 
                AND column_name = 'timeline_data'
            );
        """)
        
        result = conn.execute(check_column_query)
        column_exists = result.scalar()
        
        if not column_exists:
            # Add the timeline_data column to capture_sessions
            add_column_query = text("""
                ALTER TABLE capture_sessions 
                ADD COLUMN timeline_data TEXT;
            """)
            
            conn.execute(add_column_query)
            logger.info("Added timeline_data column to capture_sessions")
        
        logger.info("Successfully enhanced recognition data storage")
        
    except Exception as e:
        logger.error(f"Error enhancing recognition data storage: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
    
    logger.info("Completed migration: enhance_recognition_storage")
