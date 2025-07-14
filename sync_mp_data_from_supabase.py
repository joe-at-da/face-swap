#!/usr/bin/env python3
"""
Sync MP Data from Supabase to PostgreSQL

This script synchronizes Member of Parliament (MP) data from the Supabase cloud backend
to the local PostgreSQL database. It ensures that the local database contains accurate
and up-to-date MP information including names, parties, constituencies, and photo URLs.

This addresses the issue of placeholder MP names in the local database by replacing them
with authoritative data from Supabase, improving the accuracy of MP identification in videos.

Usage:
    python sync_mp_data_from_supabase.py [--dry-run]

Options:
    --dry-run    Run the script without making any changes to the database

Environment Variables:
    SUPABASE_URL                 - URL of the Supabase instance
    SUPABASE_SERVICE_ROLE_KEY    - Service role key for Supabase admin access
    POSTGRES_HOST                - PostgreSQL host (default: db)
    POSTGRES_DB                  - PostgreSQL database name (default: parliament_clips)
    POSTGRES_USER                - PostgreSQL username (default: postgres)
    POSTGRES_PASSWORD            - PostgreSQL password (default: postgres)
"""

import os
import sys
import logging
import argparse
import psycopg2
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Using service role key for admin access

# PostgreSQL connection parameters
PG_HOST = os.getenv('POSTGRES_HOST', 'db')
PG_DATABASE = os.getenv('POSTGRES_DB', 'parliament_clips')
PG_USER = os.getenv('POSTGRES_USER', 'postgres')
PG_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')

def get_supabase_client() -> Client:
    """Create and return a Supabase client.
    
    Returns:
        Client: Initialized Supabase client
        
    Raises:
        SystemExit: If connection fails or credentials are missing
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase URL or key not found in environment variables")
        sys.exit(1)
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Connected to Supabase")
        return client
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {e}")
        sys.exit(1)

def get_postgresql_connection():
    """Create and return a PostgreSQL connection.
    
    Returns:
        connection: PostgreSQL database connection
        
    Raises:
        SystemExit: If connection fails
    """
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD
        )
        logger.info(f"Connected to PostgreSQL database {PG_DATABASE} on {PG_HOST}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL database: {e}")
        sys.exit(1)

def sync_mp_data(dry_run=False):
    """Sync MP data from Supabase to PostgreSQL.
    
    This function fetches all MP data from Supabase and updates the local PostgreSQL
    database with accurate MP information, replacing placeholder names with real data.
    
    Args:
        dry_run (bool): If True, no changes will be made to the database
        
    Returns:
        bool: True if sync was successful, False otherwise
    """
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Get PostgreSQL connection
    conn = get_postgresql_connection()
    
    try:
        # Fetch all parliament members from Supabase
        response = supabase.table('parliament_members').select('*').execute()
        members = response.data
        logger.info(f"Fetched {len(members)} parliament members from Supabase")
        
        if dry_run:
            logger.info("DRY RUN: No changes will be made to the database")
        
        # Create cursor for PostgreSQL operations
        cursor = conn.cursor()
        
        # Track statistics
        updated_count = 0
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        # Process each member
        for member in members:
            try:
                # Extract member data
                member_id = member.get('parliament_id')
                if not member_id:
                    logger.warning(f"Skipping member with no parliament_id: {member.get('display_name', 'Unknown')}")
                    skipped_count += 1
                    continue
                
                # Convert member_id to integer if it's a string
                if isinstance(member_id, str):
                    try:
                        member_id = int(member_id)
                    except ValueError:
                        logger.warning(f"Skipping member with non-integer parliament_id: {member_id}")
                        skipped_count += 1
                        continue
                
                # Extract other fields using the correct Supabase field names
                display_name = member.get('display_name', 'Unknown')
                party_name = member.get('party_name', 'Unknown')
                constituency_name = member.get('constituency_name', 'Unknown')
                photo_url = member.get('photo_url', '')
                
                # Check if member exists in PostgreSQL
                cursor.execute("SELECT id FROM speakers WHERE member_id = %s", (member_id,))
                result = cursor.fetchone()
                
                if result:
                    # Update existing member
                    speaker_id = result[0]
                    if not dry_run:
                        cursor.execute(
                            "UPDATE speakers SET name = %s, party = %s, constituency = %s, photo_url = %s WHERE id = %s",
                            (display_name, party_name, constituency_name, photo_url, speaker_id)
                        )
                    updated_count += 1
                    logger.info(f"{'DRY RUN: Would update' if dry_run else 'Updated'} speaker {speaker_id} (Member ID: {member_id}) with name: {display_name}")
                else:
                    # Create new member
                    if not dry_run:
                        cursor.execute(
                            "INSERT INTO speakers (member_id, name, party, constituency, photo_url) VALUES (%s, %s, %s, %s, %s)",
                            (member_id, display_name, party_name, constituency_name, photo_url)
                        )
                    created_count += 1
                    logger.info(f"{'DRY RUN: Would create' if dry_run else 'Created'} new speaker for Member ID: {member_id} with name: {display_name}")
            
            except Exception as e:
                logger.error(f"Error processing member {member.get('parliament_id')}: {e}")
                error_count += 1
        
        # Commit changes if not dry run
        if not dry_run:
            conn.commit()
            logger.info(f"Sync completed: {updated_count} updated, {created_count} created, {skipped_count} skipped, {error_count} errors")
        else:
            logger.info(f"DRY RUN completed: Would have {updated_count} updated, {created_count} created, {skipped_count} skipped, {error_count} errors")
        
        return True
    except Exception as e:
        logger.error(f"Error syncing MP data: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Sync MP data from Supabase to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes to the database')
    args = parser.parse_args()
    
    logger.info(f"Starting MP data sync from Supabase to PostgreSQL {'(DRY RUN)' if args.dry_run else ''}")
    success = sync_mp_data(dry_run=args.dry_run)
    
    if success:
        logger.info(f"✅ MP data sync completed successfully {'(DRY RUN)' if args.dry_run else ''}")
        sys.exit(0)
    else:
        logger.error(f"❌ MP data sync failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
