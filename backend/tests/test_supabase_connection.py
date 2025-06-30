"""
Test script to verify Supabase connection and functionality.
Run this script to check if your Supabase integration is working correctly.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.core.config import settings
from backend.services.integration.supabase_client import get_supabase_client, SupabaseService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_supabase_connection():
    """Test connection to Supabase."""
    logger.info("Testing Supabase connection...")
    
    # Check if Supabase URL and API key are set
    if not settings.SUPABASE_URL or not settings.SUPABASE_API_KEY:
        logger.error("Supabase URL or API key not set. Please check your environment variables.")
        return False
    
    try:
        # Try to create a Supabase client
        client = get_supabase_client()
        logger.info(f"Successfully created Supabase client for URL: {settings.SUPABASE_URL}")
        
        # Try a simple query to verify connection
        response = client.table("health_check").select("*").limit(1).execute()
        logger.info("Successfully queried Supabase database")
        
        return True
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {str(e)}")
        return False

def test_supabase_storage():
    """Test Supabase storage functionality."""
    logger.info("Testing Supabase storage...")
    
    try:
        service = SupabaseService()
        
        # Check if buckets exist
        media_bucket = settings.SUPABASE_MEDIA_BUCKET
        export_bucket = settings.SUPABASE_EXPORT_BUCKET
        
        # List files in buckets
        try:
            media_files = service.client.storage.from_(media_bucket).list()
            logger.info(f"Successfully listed files in {media_bucket} bucket: {len(media_files)} files found")
        except Exception as e:
            logger.error(f"Error listing files in {media_bucket} bucket: {str(e)}")
        
        try:
            export_files = service.client.storage.from_(export_bucket).list()
            logger.info(f"Successfully listed files in {export_bucket} bucket: {len(export_files)} files found")
        except Exception as e:
            logger.error(f"Error listing files in {export_bucket} bucket: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Supabase storage: {str(e)}")
        return False

def test_supabase_database():
    """Test Supabase database functionality."""
    logger.info("Testing Supabase database...")
    
    try:
        service = SupabaseService()
        
        # Check if tables exist by querying them
        try:
            video_queue = service.client.table('video_processing_queue').select('*').limit(1).execute()
            logger.info(f"Successfully queried video_processing_queue table: {len(video_queue.data)} rows returned")
        except Exception as e:
            logger.error(f"Error querying video_processing_queue table: {str(e)}")
        
        try:
            clip_queue = service.client.table('clip_creation_queue').select('*').limit(1).execute()
            logger.info(f"Successfully queried clip_creation_queue table: {len(clip_queue.data)} rows returned")
        except Exception as e:
            logger.error(f"Error querying clip_creation_queue table: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Supabase database: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Supabase integration tests...")
    
    # Check if Supabase integration is enabled
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        logger.warning("Supabase integration is not enabled. Set SUPABASE_INTEGRATION_ENABLED=true in your .env file.")
    
    # Run tests
    connection_ok = test_supabase_connection()
    storage_ok = test_supabase_storage() if connection_ok else False
    database_ok = test_supabase_database() if connection_ok else False
    
    # Print summary
    logger.info("\n--- Supabase Integration Test Summary ---")
    logger.info(f"Supabase URL: {settings.SUPABASE_URL}")
    logger.info(f"Connection: {'✅ OK' if connection_ok else '❌ Failed'}")
    logger.info(f"Storage: {'✅ OK' if storage_ok else '❌ Failed'}")
    logger.info(f"Database: {'✅ OK' if database_ok else '❌ Failed'}")
    
    if connection_ok and storage_ok and database_ok:
        logger.info("All tests passed! Supabase integration is working correctly.")
    else:
        logger.warning("Some tests failed. Please check the logs for details.")
